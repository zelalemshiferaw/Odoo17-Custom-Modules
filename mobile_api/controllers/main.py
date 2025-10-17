# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, route
from odoo.exceptions import AccessDenied, ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class MobileApiController(http.Controller):
    """
    Mobile API Controller handling all API requests
    """

    def _verify_token(self):
        """
        Verify access token from request headers
        """
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Find user with valid token
        user = request.env['res.users'].sudo().search([
            ('access_token', '=', token),
            ('token_expiry_date', '>', 'now')
        ], limit=1)
        
        return user if user else None

    @route("/api/v1/auth", type="json", auth="public", methods=["POST"], csrf=False)
    def authenticate(self, **kwargs):
        """
        Endpoint for user authentication
        """
        try:
            db = kwargs.get('db')
            login = kwargs.get('login')
            password = kwargs.get('password')
            
            if not all([db, login, password]):
                return {"error": "Missing required parameters: db, login, password"}
            
            # Authenticate user
            user, token = request.env['res.users'].sudo().authenticate_user(db, login, password)
            
            if user and token:
                return {
                    "access_token": token,
                    "user_id": user.id,
                    "name": user.name,
                    "email": user.email
                }
            else:
                return {"error": "Authentication failed"}, 401
                
        except Exception as e:
            _logger.error("Authentication error: %s", str(e))
            return {"error": "Internal server error"}, 500

    @route("/api/v1/products", type="http", auth="public", methods=["GET"], csrf=False)
    def list_products(self, page=1, limit=20, **kw):
        """
        Endpoint to list products with pagination
        """
        try:
            # Verify token
            user = self._verify_token()
            if not user:
                return request.make_json_response({"error": "Unauthorized"}, 401)
            
            # Convert parameters to integers
            try:
                page = int(page)
                limit = int(limit)
            except (ValueError, TypeError):
                return request.make_json_response({"error": "Invalid page or limit parameters"}, 400)
            
            # Calculate offset
            offset = (page - 1) * limit
            
            # Search products
            product_domain = [('sale_ok', '=', True)]
            products = request.env['product.product'].with_user(user).search(
                product_domain, 
                limit=limit, 
                offset=offset
            )
            
            total_products = request.env['product.product'].with_user(user).search_count(product_domain)
            total_pages = (total_products + limit - 1) // limit if limit > 0 else 1
            
            # Prepare product data
            product_list = []
            for product in products:
                product_list.append({
                    "id": product.id,
                    "name": product.name,
                    "list_price": product.list_price,
                    "image_1920": product.image_1920.decode('utf-8') if product.image_1920 else None,
                    "qty_available": product.qty_available,
                    "description": product.description_sale or product.name,
                })
            
            response = {
                "products": product_list,
                "pager": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_items": total_products,
                    "limit": limit
                }
            }
            
            return request.make_json_response(response)
            
        except Exception as e:
            _logger.error("Product listing error: %s", str(e))
            return request.make_json_response({"error": "Internal server error"}, 500)

    @route("/api/v1/cart", type="json", auth="public", methods=["GET"], csrf=False)
    def get_cart(self, **kwargs):
        """
        Endpoint to view the contents of the shopping cart
        """
        try:
            user = self._verify_token()
            if not user:
                return {"error": "Unauthorized"}, 401
            
            cart_model = request.env['mobile.cart'].with_user(user)
            cart = cart_model.get_or_create_cart(user)
            
            cart_lines = []
            for line in cart.cart_line_ids:
                cart_lines.append({
                    "product_id": line.product_id.id,
                    "product_name": line.product_id.name,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "subtotal": line.subtotal
                })
            
            return {
                "items": cart_lines,
                "total_amount": cart.total_amount
            }
            
        except Exception as e:
            _logger.error("Get cart error: %s", str(e))
            return {"error": "Internal server error"}, 500

    @route("/api/v1/cart/add", type="json", auth="public", methods=["POST"], csrf=False)
    def add_to_cart(self, **kwargs):
        """
        Endpoint to add a product to the cart
        """
        try:
            user = self._verify_token()
            if not user:
                return {"error": "Unauthorized"}, 401
            
            product_id = kwargs.get('product_id')
            quantity = kwargs.get('quantity', 1)
            
            if not product_id:
                return {"error": "Product ID is required"}, 400
            
            cart_model = request.env['mobile.cart'].with_user(user)
            cart = cart_model.get_or_create_cart(user)
            
            cart.add_product(product_id, quantity)
            
            return {
                "success": True,
                "message": "Product added to cart"
            }
            
        except ValidationError as ve:
            return {"error": str(ve)}, 400
        except Exception as e:
            _logger.error("Add to cart error: %s", str(e))
            return {"error": "Internal server error"}, 500

    @route("/api/v1/cart/update", type="json", auth="public", methods=["PUT"], csrf=False)
    def update_cart(self, **kwargs):
        """
        Endpoint to update the quantity of a product in the cart
        """
        try:
            user = self._verify_token()
            if not user:
                return {"error": "Unauthorized"}, 401
            
            product_id = kwargs.get('product_id')
            quantity = kwargs.get('quantity')
            
            if not product_id or quantity is None:
                return {"error": "Product ID and quantity are required"}, 400
            
            cart_model = request.env['mobile.cart'].with_user(user)
            cart = cart_model.get_or_create_cart(user)
            
            cart.update_quantity(product_id, quantity)
            
            return {
                "success": True,
                "message": "Cart updated successfully"
            }
            
        except ValidationError as ve:
            return {"error": str(ve)}, 400
        except Exception as e:
            _logger.error("Update cart error: %s", str(e))
            return {"error": "Internal server error"}, 500

    @route("/api/v1/cart/remove", type="json", auth="public", methods=["DELETE"], csrf=False)
    def remove_from_cart(self, **kwargs):
        """
        Endpoint to remove a product from the cart
        """
        try:
            user = self._verify_token()
            if not user:
                return {"error": "Unauthorized"}, 401
            
            product_id = kwargs.get('product_id')
            
            if not product_id:
                return {"error": "Product ID is required"}, 400
            
            cart_model = request.env['mobile.cart'].with_user(user)
            cart = cart_model.get_or_create_cart(user)
            
            cart.remove_product(product_id)
            
            return {
                "success": True,
                "message": "Product removed from cart"
            }
            
        except ValidationError as ve:
            return {"error": str(ve)}, 400
        except Exception as e:
            _logger.error("Remove from cart error: %s", str(e))
            return {"error": "Internal server error"}, 500

    @route("/api/v1/order/create", type="json", auth="public", methods=["POST"], csrf=False)
    def create_order(self, **kwargs):
        """
        Endpoint to create a sales order from the cart
        """
        try:
            user = self._verify_token()
            if not user:
                return {"error": "Unauthorized"}, 401
            
            cart_model = request.env['mobile.cart'].with_user(user)
            cart = cart_model.get_or_create_cart(user)
            
            if not cart.cart_line_ids:
                return {"error": "Cart is empty"}, 400
            
            # Prepare cart data for order creation
            cart_data = {
                'lines': []
            }
            for line in cart.cart_line_ids:
                cart_data['lines'].append({
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'unit_price': line.unit_price,
                })
            
            # Create sales order
            sale_order_model = request.env['sale.order'].with_user(user)
            order = sale_order_model.create_from_cart(user, cart_data)
            
            # Clear the cart
            cart.clear_cart()
            
            return {
                "success": True,
                "message": "Order created successfully",
                "order_id": order.id,
                "order_name": order.name,
                "amount_total": order.amount_total
            }
            
        except ValidationError as ve:
            return {"error": str(ve)}, 400
        except Exception as e:
            _logger.error("Create order error: %s", str(e))
            return {"error": "Internal server error"}, 500

    @route("/api/v1/logout", type="json", auth="public", methods=["POST"], csrf=False)
    def logout(self, **kwargs):
        """
        Endpoint to logout and clear access token
        """
        try:
            user = self._verify_token()
            if not user:
                return {"error": "Unauthorized"}, 401
            
            user.clear_access_token()
            
            return {
                "success": True,
                "message": "Logged out successfully"
            }
            
        except Exception as e:
            _logger.error("Logout error: %s", str(e))
            return {"error": "Internal server error"}, 500