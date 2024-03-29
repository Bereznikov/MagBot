class Customer:
    def __init__(self, customer_id, first_name, last_name, username, phone=None, country=None, shop=None, section=None,
                 category=None, number=1, cart=None, products_from_category=None, connection=None,
                 address=None, shipper=None, cart_position=None, number_of_products=None):
        self.id = customer_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.phone = phone
        self.country = country

        self.shop = shop
        self.section = section
        self.category = category
        self.number = number
        self.cart = cart
        self.cart_position = cart_position
        self.number_of_products = number_of_products
        self.products_from_category = products_from_category
        self.address = address
        self.shipper = shipper

        self.connection = connection

    def __str__(self):
        return f"{self.id} {self.username} {self.first_name} {self.last_name} {self.shop} {self.section} " \
               f"{self.category} {self.cart} {self.connection}"

    def go_shopping(self):
        self.cart = []

    def add_to_cart(self, product_id, quantity):
        self.cart.append(product_id, quantity)
