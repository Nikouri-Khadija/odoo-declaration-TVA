# ---------------------------------------------------------------------------
# Constantes TVA EDI SIMPL-TVA
# Toutes les valeurs de sélection sont définies ici et importées ailleurs.
# ---------------------------------------------------------------------------

# Codes EDI → libellés
PAYMENT_MODE_CODES = {
    '1': 'Espèces',
    '2': 'Chèque',
    '3': 'Prélèvement',
    '4': 'Virement',
    '7': 'Autres',
}

PAYMENT_MODE_DEFAULT = '7'

# Listes de sélection pour les champs Odoo
PAYMENT_MODE_SELECTION = [(k, f"{k} - {v}") for k, v in PAYMENT_MODE_CODES.items()]

REGIME_SELECTION = [
    ('1', 'Mensuel'),
    ('2', 'Trimestriel'),
]

MOIS_SELECTION = [
    ('1',  'Janvier'),  ('2',  'Février'),   ('3',  'Mars'),
    ('4',  'Avril'),    ('5',  'Mai'),        ('6',  'Juin'),
    ('7',  'Juillet'),  ('8',  'Août'),       ('9',  'Septembre'),
    ('10', 'Octobre'),  ('11', 'Novembre'),   ('12', 'Décembre'),
]

TRIMESTRE_SELECTION = [
    ('1', 'T1 (Janvier - Mars)'),
    ('2', 'T2 (Avril - Juin)'),
    ('3', 'T3 (Juillet - Septembre)'),
    ('4', 'T4 (Octobre - Décembre)'),
]