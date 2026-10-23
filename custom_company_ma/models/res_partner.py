from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    ice = fields.Char(
        string='ICE',
        help="Identifiant Commun de l'Entreprise du fournisseur"
    )

    if_code = fields.Char(
        string='IF',
        help="Identifiant Fiscal du fournisseur"
    )