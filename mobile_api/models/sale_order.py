# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create_from_cart(self, user, cart_data):
        """
        Create a sales order from cart data
        """
        # Get or create partner if needed
        partner = user.partner_id
        
        # Prepare order lines from cart data
        order_lines = []
        for line in cart_data.get('lines', []):
            product = self.env['product.product'].browse(line['product_id'])
            order_lines.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': line['quantity'],
                'price_unit': line.get('unit_price', product.list_price),
                'name': product.name,
            }))

        # Create the sales order
        order_vals = {
            'partner_id': partner.id,
            'user_id': user.id,
            'order_line': order_lines,
        }
        
        order = self.create(order_vals)
        return order