class ActiveCustomers:
    def __init__(self, connection):
        self.customers = None
        self.connection = connection

    def __str__(self):
        if self.customers is None:
            return 'Покупателей нет'
        else:
            return '\n'.join([str(c) for c in self.customers])

    def add_customer(self, customer):
        if self.customers is None:
            self.customers = {customer.id: customer}
        else:
            self.customers[customer.id] = customer

    def delete_customer(self, customer):
        self.customers.pop(customer.id, None)


class Customer:
    def __init__(self, customer_id, first_name, last_name, username, phone=None, country=None, shop=None, section=None,
                 category=None, number=1, cart=None, products_from_category=None, current_product_id=None,
                 connection=None, address=None, shipper=None):
        self.id = customer_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.phone = phone
        self.country = country

        self.shop = shop
        self.section = section
        self.category = category
        self.nuber = number
        self.cart = cart
        self.products_from_category = products_from_category
        self.current_product_id = current_product_id
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
