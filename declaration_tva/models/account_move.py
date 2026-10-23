from odoo import api, fields, models

from ..constants import PAYMENT_MODE_CODES
from ..payment_utils import get_payment_info, payment_to_mp_code


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Suivi de la déclaration ────────────────────────────────────────────
    tva_declared = fields.Boolean(
        string='Déclarée TVA',
        default=False,
        copy=False,
        help="Indique si cette facture a déjà été incluse dans une déclaration TVA EDI.",
    )
    tva_declaration_date = fields.Date(
        string='Date de déclaration',
        copy=False,
    )
    tva_declaration_period = fields.Char(
        string='Période déclarée',
        copy=False,
        help="Ex : 2024-T1 ou 2024-10",
    )
    tva_declaration_id = fields.Many2one(
        'declaration.tva.edi',
        string='Déclaration TVA',
        copy=False,
    )

    # ── Informations paiement (calculées) ─────────────────────────────────
    payment_mode_display = fields.Char(
        string='Mode de paiement',
        compute='_compute_payment_info',
        store=False,
    )
    payment_date_display = fields.Date(
        string='Date de paiement',
        compute='_compute_payment_info',
        store=False,
    )

    @api.depends('payment_state')
    def _compute_payment_info(self):
        for move in self:
            date, code = get_payment_info(move)
            move.payment_mode_display = PAYMENT_MODE_CODES.get(code, 'Autres') if date else ''
            move.payment_date_display = date or False
