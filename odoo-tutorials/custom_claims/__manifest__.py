{
    'name': 'Gestió de Reclamacions',
    'version': '1.0',
    'summary': 'Mòdul per gestionar les reclamacions dels clients',
    'description': 'Permet gestionar les reclamacions dels clients, incloent estat, missatges i accions relacionades.',
    'author': 'El teu nom',
    'depends': ['base', 'sale', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/claim_views.xml',
        'views/claim_menus.xml',
    ],
    'installable': True,
    'application': True,
}

