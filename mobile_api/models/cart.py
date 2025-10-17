# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MobileCart(models.Model):
    _name = 'mobile.cart'
    _description = 'Mobile Shopping Cart'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    cart_line_ids = fields.One2many('mobile.cart.line', 'cart_id', string='Cart Lines')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)

    @api.depends('cart_line_ids.subtotal')
    def _compute_total_amount(self):
        for cart in self:
            cart.total_amount = sum(line.subtotal for line in cart.cart_line_ids)

    def get_or_create_cart(self, user):
        """
        Get existing cart or create a new one for the user
        """
        cart = self.search([('user_id', '=', user.id)], limit=1)
        if not cart:
            cart = self.create({'user_id': user.id})
            user.write({'mobile_cart_id': cart.id})
        return cart

    def add_product(self, product_id, quantity=1):
        """
        Add product to cart or update quantity if already exists
        """
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)
        
        if not product.exists():
            raise ValidationError("Product not found")
        
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        # Check if product already in cart
        existing_line = self.cart_line_ids.filtered(lambda l: l.product_id.id == product_id)
        
        if existing_line:
            existing_line.quantity += quantity
        else:
            self.env['mobile.cart.line'].create({
                'cart_id': self.id,
                'product_id': product_id,
                'quantity': quantity,
                'unit_price': product.list_price
            })
        
        return True

    def update_quantity(self, product_id, quantity):
        """
        Update product quantity in cart
        """
        self.ensure_one()
        if quantity < 0:
            raise ValidationError("Quantity cannot be negative")
        
        line = self.cart_line_ids.filtered(lambda l: l.product_id.id == product_id)
        if not line:
            raise ValidationError("Product not found in cart")
        
        if quantity == 0:
            line.unlink()
        else:
            line.quantity = quantity
        
        return True

    def remove_product(self, product_id):
        """
        Remove product from cart
        """
        self.ensure_one()
        line = self.cart_line_ids.filtered(lambda l: l.product_id.id == product_id)
        if line:
            line.unlink()
        return True

    def clear_cart(self):
        """
        Clear all items from cart
        """
        self.ensure_one()
        self.cart_line_ids.unlink()
        return True


class MobileCartLine(models.Model):
    _name = 'mobile.cart.line'
    _description = 'Mobile Cart Line'

    cart_id = fields.Many2one('mobile.cart', string='Cart', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.model
    def create(self, vals):
        # Ensure unit_price is set from product if not provided
        if 'unit_price' not in vals and 'product_id' in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            vals['unit_price'] = product.list_price
        return super().create(vals)