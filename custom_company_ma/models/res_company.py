from odoo import fields, models 
 
class ResCompany(models.Model): 
    _inherit = 'res.company' 
 
    identifiant_fiscal = fields.Char( 
        string='Identifiant Fiscal', 
        help="Identifiant Fiscal de l'entreprise" 
    ) 
