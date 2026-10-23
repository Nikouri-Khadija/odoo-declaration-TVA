import base64
import io
import zipfile
from datetime import date
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..constants import (
    PAYMENT_MODE_SELECTION,
    REGIME_SELECTION,
    MOIS_SELECTION,
    TRIMESTRE_SELECTION,
)
from ..payment_utils import get_payment_info



# Wizard principal


class WizardDeclarationTva(models.TransientModel):
    _name = 'wizard.declaration.tva'
    _description = 'Wizard Déclaration TVA EDI SIMPL-TVA'

    # Étape 1 : Champs que l'utilisateur saisit
    company_id = fields.Many2one(
        'res.company', string='Société', required=True,
        default=lambda self: self.env.company,
    )
    annee = fields.Integer(
        string='Année', required=True,
        default=lambda self: date.today().year,
    )
    regime = fields.Selection(
        selection=REGIME_SELECTION, string='Régime', required=True, default='1',
    )
    periode_mensuelle = fields.Selection(
        selection=MOIS_SELECTION, string='Mois',
    )
    periode_trimestrielle = fields.Selection(
        selection=TRIMESTRE_SELECTION, string='Trimestre',
    )
    prorata = fields.Float(string='Prorata (%)', default=100.0, required=True)
    forcer_redeclaration = fields.Boolean(
        string='Forcer la re-déclaration', default=False,
        help="Inclure des factures déjà déclarées.",
    )

    # ── État et lignes ────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[('params', 'Paramètres'), ('preview', 'Synthèse')],
        default='params',
    )
    line_ids = fields.One2many('wizard.declaration.tva.line', 'wizard_id', string='Lignes')
    move_ids_context = fields.Many2many(
        'account.move', 'wizard_tva_move_ctx_rel', 'wizard_id', 'move_id',
        string='Factures sélectionnées',
    )
    has_already_declared = fields.Boolean(compute='_compute_has_already_declared')

    # ── Onchange : si régime change → reset période ───────────────────────
    @api.onchange('regime')
    def _onchange_regime(self):
        self.periode_mensuelle = False
        self.periode_trimestrielle = False

    @api.depends('line_ids.already_declared')
    def _compute_has_already_declared(self):
        for rec in self:
            rec.has_already_declared = any(rec.line_ids.mapped('already_declared'))

    # ── Bouton 1 : Générer la déclaration (Étape 1 → 2) ──────────────────
    def action_generer_declaration(self):
        self.ensure_one()

        # Validations
        if not self.company_id.identifiant_fiscal:
            raise UserError(
                _("L'Identifiant Fiscal (IF) de la société « %s » n'est pas renseigné.")
                % self.company_id.name
            )
        if not self._get_periode_value():
            raise UserError(_("Veuillez sélectionner une période."))

        # Récupération des factures
        active_ids = self.env.context.get('active_ids', []) or self.move_ids_context.ids
        moves = self.env['account.move'].browse(active_ids).filtered(
            lambda m: m.move_type == 'in_invoice' and m.state == 'posted'
        )
        if not moves:
            raise UserError(_("Aucune facture fournisseur validée sélectionnée."))

        # Vérification re-déclaration
        already_declared = moves.filtered(lambda m: m.tva_declared)
        if already_declared and not self.forcer_redeclaration:
            names = ', '.join(already_declared.mapped('name'))
            raise UserError(
                _("Les factures suivantes ont déjà été déclarées :\n%s\n\n"
                  "Cochez « Forcer la re-déclaration » pour les inclure quand même.") % names
            )

        # Construction des lignes
        lines = [(0, 0, self._build_line_vals(idx, move)) for idx, move in enumerate(moves, start=1)]
        self.write({
            'line_ids': [(5, 0, 0)] + lines,
            'state': 'preview',
            'move_ids_context': [(6, 0, moves.ids)],
        })
        return self._reopen_wizard()

    # ── Bouton 2 : Confirmer et générer le XML ────────────────────────────
    def action_confirmer_et_generer(self):
        self.ensure_one()

        if not self.line_ids:
            raise UserError(_("Aucune ligne de déclaration à générer."))

        periode_val = self._get_periode_value()
        if_societe  = self.company_id.identifiant_fiscal

        # Construction XML
        xml_bytes = self._build_xml(if_societe, periode_val)

        # Nommage du fichier
        periode_slug = self._get_periode_label().replace(' ', '_').replace('(', '').replace(')', '')
        xml_filename = f"TVA_EDI_{self.annee}_{periode_slug}_{if_societe}.xml"
        zip_filename = xml_filename.replace('.xml', '.zip')

        # Compression ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(xml_filename, xml_bytes)
        zip_b64 = base64.b64encode(zip_buffer.getvalue())

        # Création de l'enregistrement déclaration
        declaration = self.env['declaration.tva.edi'].create({
            'company_id':   self.company_id.id,
            'annee':        self.annee,
            'regime':       self.regime,
            'periode':      periode_val,
            'prorata':      self.prorata,
            'state':        'done',
            'xml_file':     zip_b64,
            'xml_filename': zip_filename,
            'move_ids':     [(6, 0, self.move_ids_context.ids)],
        })

        # Marquage des factures
        periode_label_full = f"{self.annee}-{self._get_periode_label()}"
        self.move_ids_context.write({
            'tva_declared':           True,
            'tva_declaration_date':   fields.Date.today(),
            'tva_declaration_period': periode_label_full,
            'tva_declaration_id':     declaration.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'declaration.tva.edi',
            'res_id': declaration.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Bouton 3 : Retour aux paramètres ─────────────────────────────────
    def action_retour_params(self):
        self.write({'state': 'params', 'line_ids': [(5, 0, 0)]})
        return self._reopen_wizard()

    # ── Génération XML ────────────────────────────────────────────────────
    def _build_xml(self, if_societe, periode_val):
        root = etree.Element('DeclarationReleveDeduction')
        etree.SubElement(root, 'identifiantFiscal').text = str(if_societe)
        etree.SubElement(root, 'annee').text             = str(self.annee)
        etree.SubElement(root, 'periode').text           = str(periode_val)
        etree.SubElement(root, 'regime').text            = str(self.regime)

        releve = etree.SubElement(root, 'releveDeductions')
        for line in self.line_ids:
            self._build_xml_line(releve, line)

        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def _build_xml_line(self, parent, line):
        rd = etree.SubElement(parent, 'rd')
        etree.SubElement(rd, 'ord').text = str(line.ord)
        etree.SubElement(rd, 'num').text = str(line.num or '')
        etree.SubElement(rd, 'des').text = str(line.des or '')
        etree.SubElement(rd, 'mht').text = f"{line.mht:.2f}"
        etree.SubElement(rd, 'tva').text = f"{line.tva:.2f}"
        etree.SubElement(rd, 'ttc').text = f"{line.ttc:.2f}"

        refF = etree.SubElement(rd, 'refF')
        etree.SubElement(refF, 'if').text  = str(line.partner_if or '')
        etree.SubElement(refF, 'nom').text = str(line.partner_nom or '')
        etree.SubElement(refF, 'ice').text = str(line.partner_ice or '')

        etree.SubElement(rd, 'tx').text      = f"{line.tx:.2f}"
        etree.SubElement(rd, 'prorata').text = f"{line.prorata:.0f}"

        mp = etree.SubElement(rd, 'mp')
        etree.SubElement(mp, 'id').text = str(line.mp_id or '7')

        etree.SubElement(rd, 'dpai').text = str(line.dpai) if line.dpai else ''
        etree.SubElement(rd, 'dfac').text = str(line.dfac) if line.dfac else ''

    # ── Helpers internes ──────────────────────────────────────────────────
    def _reopen_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context),
        }

    def _get_periode_value(self):
        if self.regime == '1':
            return self.periode_mensuelle or ''
        return self.periode_trimestrielle or ''

    def _get_periode_label(self):
        if self.regime == '1':
            return dict(self._fields['periode_mensuelle'].selection).get(self.periode_mensuelle, '')
        return dict(self._fields['periode_trimestrielle'].selection).get(self.periode_trimestrielle, '')

    def _get_dominant_tax_rate(self, move):
        for line in move.invoice_line_ids:
            for tax in line.tax_ids:
                return abs(tax.amount)
        return 0.0

    def _build_line_vals(self, idx, move):
        dpai, mp_code = get_payment_info(move)
        partner = move.partner_id
        return {
            'move_id':      move.id,
            'ord':          idx,
            'num':          move.name or '',
            'dfac':         move.invoice_date,
            'des':          move.invoice_line_ids[0].name if move.invoice_line_ids else '',
            'partner_nom':  partner.name or '',
            'partner_if':   partner.if_code or '',
            'partner_ice':  partner.ice or '',
            'mht':          move.amount_untaxed,
            'tx':           self._get_dominant_tax_rate(move),
            'tva':          move.amount_tax,
            'ttc':          move.amount_total,
            'prorata':      self.prorata,
            'mp_id':        mp_code,
            'dpai':         dpai or move.invoice_date,
            'already_declared': move.tva_declared,
        }


# ---------------------------------------------------------------------------
# Ligne du wizard (une facture = une ligne)
# ---------------------------------------------------------------------------

class WizardDeclarationTvaLine(models.TransientModel):
    _name = 'wizard.declaration.tva.line'
    _description = 'Ligne du wizard Déclaration TVA'

    wizard_id    = fields.Many2one('wizard.declaration.tva', ondelete='cascade')
    move_id      = fields.Many2one('account.move', string='Facture', readonly=True)
    ord          = fields.Integer(string='N°')
    num          = fields.Char(string='N° Facture')
    dfac         = fields.Date(string='Date Facture')
    des          = fields.Char(string='Désignation')
    partner_nom  = fields.Char(string='Fournisseur')
    partner_if   = fields.Char(string='IF')
    partner_ice  = fields.Char(string='ICE')
    mht          = fields.Float(string='Montant HT',   digits=(16, 2))
    tx           = fields.Float(string='Taux TVA (%)', digits=(16, 2))
    tva          = fields.Float(string='Montant TVA',  digits=(16, 2))
    ttc          = fields.Float(string='Montant TTC',  digits=(16, 2))
    prorata      = fields.Float(string='Prorata (%)',  digits=(16, 2))
    mp_id        = fields.Selection(selection=PAYMENT_MODE_SELECTION, string='Mode Paiement', default='7')
    dpai         = fields.Date(string='Date Paiement')
    already_declared = fields.Boolean(string='Déjà déclarée', readonly=True)