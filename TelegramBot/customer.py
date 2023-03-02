class Customer:
    def __init__(self, customer_id, first_name, last_name, username, phone=None, country=None):
        self.id = customer_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.phone = phone
        self.country = country
        self.cart = None

    def __str__(self):
        return f"{self.id} {self.username} {self.first_name} {self.last_name}"

    def go_shopping(self):
        self.cart = []

    def add_to_cart(self, product_id, quantity):
        self.cart.append(product_id, quantity)
