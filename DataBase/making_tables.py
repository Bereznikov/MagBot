"""CREATE TABLE IF NOT EXISTS public.shop
(
    shop_id integer NOT NULL,
    shop_name character varying COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT shop_pkey PRIMARY KEY (shop_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.shop
    OWNER to postgres;"""""

