from odoo import api, fields, models
from ..constants import REGIME_SELECTION


class DeclarationTvaEdi(models.Model):
    _name = 'declaration.tva.edi'
    _description = 'Déclaration TVA EDI SIMPL-TVA'
    _order = 'date_declaration desc, id desc'

    
    annee = fields.Integer(string='Année', required=True)
    regime = fields.Selection(
        selection=REGIME_SELECTION,   # ← importé depuis constants.py
        string='Régime',
        required=True,
    )
    periode = fields.Char(
        string='Période',
        required=True,
        help="Mois (1-12) pour régime mensuel, T1/T2/T3/T4 pour trimestriel.",
    )
    prorata = fields.Float(
        string='Prorata (%)',
        default=100.0,
        help="Pourcentage de prorata de déduction TVA.",
    )
    date_declaration = fields.Date(
        string='Date de déclaration',
        required=True,
        default=fields.Date.today,
    )
    state = fields.Selection(
        selection=[('draft', 'Brouillon'), ('done', 'Généré')],
        string='Statut',
        default='draft',
        readonly=True,
    )


    #les champs spéciaux
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    move_ids = fields.Many2many(
        'account.move',
        'declaration_tva_move_rel',
        'declaration_id',
        'move_id',
        string='Factures déclarées',
    )

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('declaration.tva.edi') or 'Nouveau',
    )

    xml_file = fields.Binary(string='Fichier ZIP', attachment=True, readonly=True)
    xml_filename = fields.Char(string='Nom du fichier ZIP', readonly=True)
    
    nb_factures = fields.Integer(
        string='Nombre de factures',
        compute='_compute_nb_factures',
    )
    

    @api.depends('move_ids')
    def _compute_nb_factures(self):
        for rec in self:
            rec.nb_factures = len(rec.move_ids)