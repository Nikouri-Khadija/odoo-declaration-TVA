{
    'name': 'Déclaration TVA ',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Génération du relevé de déduction TVA ',
    'description': """
        Génération de la déclaration TVA EDI conforme au cahier des charges SIMPL-TVA v2.0.
        - Sélection des factures fournisseurs à déclarer
        - Wizard de configuration (année, régime, période, prorata)
        - Tableau de synthèse modifiable avant confirmation
        - Génération du fichier XML compressé en ZIP
        - Marquage automatique des factures déclarées
    """,
    'author': 'Custom nikouri',
    # Hérite des champs marocains (identifiant_fiscal, ice, if_code)
    'depends': ['account', 'custom_company_ma'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/declaration_tva_views.xml',
        'wizard/wizard_declaration_tva_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
