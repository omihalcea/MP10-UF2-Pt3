{
    'name': 'Gestió de Reclamacions',
    'version': '1.0',
    'summary': 'Gestió de reclamacions de clients',
    'category': 'Customer Relationship Management',
    'depends': ['sale', 'stock', 'sale_stock', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/sequences.xml',
        'views/claim_views.xml',
        'views/claim_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
