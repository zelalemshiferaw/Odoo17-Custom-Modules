{
    'name': 'Mobile API',
    'version': '17.0.1.0.0',
    'category': 'API',
    'summary': 'REST API for Mobile E-commerce',
    'description': """
        Provides REST API endpoints for mobile applications including:
        - User authentication with token
        - Product listing with pagination
        - Shopping cart management
        - Order creation
    """,
    'author': 'Zelalem Shiferaw',
    'depends': ['base', 'web', 'sale', 'product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/cart.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}