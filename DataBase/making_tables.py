"""
CREATE TABLE IF NOT EXISTS public.shop
(
    shop_id integer NOT NULL,
    shop_name character varying COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT shop_pkey PRIMARY KEY (shop_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.shop
    OWNER to postgres;




CREATE TABLE IF NOT EXISTS public.section
(
    section_id integer NOT NULL,
    section_name character varying COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT section_pkey PRIMARY KEY (section_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.section
    OWNER to postgres;






CREATE TABLE IF NOT EXISTS public.category
(
    category_id integer NOT NULL,
    category_name character varying COLLATE pg_catalog."default" NOT NULL,
    section_id integer NOT NULL,
    CONSTRAINT category_pkey PRIMARY KEY (category_id),
    CONSTRAINT section_id_foreign_key FOREIGN KEY (section_id)
        REFERENCES public.section (section_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.category
    OWNER to postgres;

COMMENT ON CONSTRAINT section_id_foreign_key ON public.category
    IS 'simple foreign key';








CREATE TABLE IF NOT EXISTS public.product
(
    product_id integer NOT NULL,
    product_name character varying COLLATE pg_catalog."default" NOT NULL,
    price numeric NOT NULL,
    price_high numeric,
    product_link character varying COLLATE pg_catalog."default" NOT NULL,
    image_link character varying COLLATE pg_catalog."default",
    category_id integer NOT NULL,
    shop_id integer NOT NULL,
    description character varying COLLATE pg_catalog."default",
    availability boolean,
    CONSTRAINT product_pkey PRIMARY KEY (product_id),
    CONSTRAINT category_id_foreign_key FOREIGN KEY (category_id)
        REFERENCES public.category (category_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT shop_id_foreign_key FOREIGN KEY (shop_id)
        REFERENCES public.shop (shop_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.product
    OWNER to postgres;







CREATE TABLE public.status
(
    status_id integer,
    status_name character varying NOT NULL,
    PRIMARY KEY (status_id)
);

ALTER TABLE IF EXISTS public.status
    OWNER to postgres;





CREATE TABLE public.shipper
(
    shipper_id integer NOT NULL,
    shipper_name character varying NOT NULL,
    shipper_link character varying,
    PRIMARY KEY (shipper_id)
);

ALTER TABLE IF EXISTS public.shipper
    OWNER to postgres;





CREATE TABLE public.customer
(
    customer_id integer NOT NULL,
    first_name character varying,
    last_name character varying,
    username character varying,
    phone character varying,
    country character varying,
    PRIMARY KEY (customer_id)
);

ALTER TABLE IF EXISTS public.customer
    OWNER to postgres;



CREATE TABLE IF NOT EXISTS public."order"
(
    order_id integer NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
    customer_id integer NOT NULL,
    order_time timestamp with time zone,
    send_time timestamp with time zone,
    shipped_time timestamp with time zone,
    ship_adress character varying COLLATE pg_catalog."default",
    shipper_id integer NOT NULL,
    status_id integer NOT NULL,
    CONSTRAINT order_pkey PRIMARY KEY (order_id),
    CONSTRAINT customer_id_foreign_key FOREIGN KEY (customer_id)
        REFERENCES public.customer (customer_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT shipper_id_foreign_key FOREIGN KEY (shipper_id)
        REFERENCES public.shipper (shipper_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT staus_id_fireign_key FOREIGN KEY (status_id)
        REFERENCES public.status (status_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."order"
    OWNER to postgres;



CREATE TABLE IF NOT EXISTS public.order_detail
(
    order_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity integer DEFAULT 1,
    CONSTRAINT order_detail_pkey PRIMARY KEY (order_id, product_id),
    CONSTRAINT order_id_foreign_key FOREIGN KEY (order_id)
        REFERENCES public."order" (order_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT product_id FOREIGN KEY (product_id)
        REFERENCES public.product (product_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.order_detail
    OWNER to postgres;

"""