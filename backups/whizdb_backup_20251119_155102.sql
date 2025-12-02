--
-- PostgreSQL database dump
--

\restrict EphQ6ovQZUi73YuWJuJV5AGsXyViCS9hVX8HaAXbaWcMgQ2BbhYSSzhoTg7V6yI

-- Dumped from database version 15.14 (Debian 15.14-1.pgdg13+1)
-- Dumped by pg_dump version 15.14 (Debian 15.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.orders DROP CONSTRAINT IF EXISTS orders_product_id_fkey;
DROP INDEX IF EXISTS public.idx_run_metrics_journey;
DROP INDEX IF EXISTS public.idx_products_category;
DROP INDEX IF EXISTS public.idx_orders_number;
DROP INDEX IF EXISTS public.idx_orders_email;
DROP INDEX IF EXISTS public.idx_customer_context_last_interaction;
DROP INDEX IF EXISTS public.idx_audit_log_timestamp;
DROP INDEX IF EXISTS public.idx_audit_log_run_id;
ALTER TABLE IF EXISTS ONLY public.products DROP CONSTRAINT IF EXISTS products_pkey;
ALTER TABLE IF EXISTS ONLY public.orders DROP CONSTRAINT IF EXISTS orders_pkey;
ALTER TABLE IF EXISTS ONLY public.orders DROP CONSTRAINT IF EXISTS orders_order_number_key;
ALTER TABLE IF EXISTS ONLY public.customer_context DROP CONSTRAINT IF EXISTS customer_context_pkey;
ALTER TABLE IF EXISTS ONLY public.agent_run_metrics DROP CONSTRAINT IF EXISTS agent_run_metrics_run_id_key;
ALTER TABLE IF EXISTS ONLY public.agent_run_metrics DROP CONSTRAINT IF EXISTS agent_run_metrics_pkey;
ALTER TABLE IF EXISTS ONLY public.agent_audit_log DROP CONSTRAINT IF EXISTS agent_audit_log_pkey;
ALTER TABLE IF EXISTS public.products ALTER COLUMN product_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.orders ALTER COLUMN order_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.agent_run_metrics ALTER COLUMN metric_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.agent_audit_log ALTER COLUMN log_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.products_product_id_seq;
DROP TABLE IF EXISTS public.products;
DROP SEQUENCE IF EXISTS public.orders_order_id_seq;
DROP TABLE IF EXISTS public.orders;
DROP TABLE IF EXISTS public.customer_context;
DROP SEQUENCE IF EXISTS public.agent_run_metrics_metric_id_seq;
DROP TABLE IF EXISTS public.agent_run_metrics;
DROP SEQUENCE IF EXISTS public.agent_audit_log_log_id_seq;
DROP TABLE IF EXISTS public.agent_audit_log;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_audit_log (
    log_id integer NOT NULL,
    run_id character varying(255) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    event_type character varying(50),
    event_details jsonb,
    status character varying(50),
    error_message text
);


--
-- Name: agent_audit_log_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_audit_log_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_audit_log_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_audit_log_log_id_seq OWNED BY public.agent_audit_log.log_id;


--
-- Name: agent_run_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_run_metrics (
    metric_id integer NOT NULL,
    run_id character varying(255) NOT NULL,
    journey_name character varying(255),
    start_time timestamp with time zone,
    end_time timestamp with time zone,
    duration_ms integer,
    final_outcome character varying(50),
    ticket_id character varying(255)
);


--
-- Name: agent_run_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_run_metrics_metric_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_run_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_run_metrics_metric_id_seq OWNED BY public.agent_run_metrics.metric_id;


--
-- Name: customer_context; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_context (
    customer_id character varying(255) NOT NULL,
    last_interaction_date timestamp with time zone,
    total_interactions integer DEFAULT 1,
    total_denials integer DEFAULT 0,
    custom_notes jsonb
);


--
-- Name: orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders (
    order_id integer NOT NULL,
    order_number character varying(50) NOT NULL,
    customer_email character varying(255),
    product_id integer,
    quantity integer NOT NULL,
    total_amount numeric(10,2) NOT NULL,
    order_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    status character varying(50) DEFAULT 'pending'::character varying
);


--
-- Name: orders_order_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.orders_order_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: orders_order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.orders_order_id_seq OWNED BY public.orders.order_id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.products (
    product_id integer NOT NULL,
    product_name character varying(255) NOT NULL,
    description text,
    price numeric(10,2) NOT NULL,
    category character varying(100),
    stock_quantity integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: products_product_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.products_product_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: products_product_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.products_product_id_seq OWNED BY public.products.product_id;


--
-- Name: agent_audit_log log_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_audit_log ALTER COLUMN log_id SET DEFAULT nextval('public.agent_audit_log_log_id_seq'::regclass);


--
-- Name: agent_run_metrics metric_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_run_metrics ALTER COLUMN metric_id SET DEFAULT nextval('public.agent_run_metrics_metric_id_seq'::regclass);


--
-- Name: orders order_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders ALTER COLUMN order_id SET DEFAULT nextval('public.orders_order_id_seq'::regclass);


--
-- Name: products product_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products ALTER COLUMN product_id SET DEFAULT nextval('public.products_product_id_seq'::regclass);


--
-- Data for Name: agent_audit_log; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_audit_log (log_id, run_id, "timestamp", event_type, event_details, status, error_message) FROM stdin;
\.


--
-- Data for Name: agent_run_metrics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_run_metrics (metric_id, run_id, journey_name, start_time, end_time, duration_ms, final_outcome, ticket_id) FROM stdin;
\.


--
-- Data for Name: customer_context; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.customer_context (customer_id, last_interaction_date, total_interactions, total_denials, custom_notes) FROM stdin;
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.orders (order_id, order_number, customer_email, product_id, quantity, total_amount, order_date, status) FROM stdin;
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.products (product_id, product_name, description, price, category, stock_quantity, created_at) FROM stdin;
1	Wireless Headphones	Premium noise-canceling wireless headphones with 30-hour battery life	199.99	Electronics	45	2025-11-18 18:43:09.366441
2	Smart Watch	Fitness tracking smartwatch with heart rate monitor and GPS	299.99	Electronics	32	2025-11-18 18:43:09.366441
3	Laptop Stand	Ergonomic aluminum laptop stand with adjustable height	49.99	Accessories	78	2025-11-18 18:43:09.366441
4	USB-C Hub	7-in-1 USB-C hub with HDMI, USB 3.0, and SD card reader	39.99	Accessories	120	2025-11-18 18:43:09.366441
5	Mechanical Keyboard	RGB backlit mechanical gaming keyboard with Cherry MX switches	149.99	Electronics	28	2025-11-18 18:43:09.366441
6	Wireless Mouse	Ergonomic wireless mouse with precision tracking	59.99	Accessories	95	2025-11-18 18:43:09.366441
7	Phone Case	Protective silicone case with raised edges for screen protection	19.99	Accessories	200	2025-11-18 18:43:09.366441
8	Portable Charger	20000mAh portable power bank with fast charging	44.99	Electronics	65	2025-11-18 18:43:09.366441
9	Bluetooth Speaker	Waterproof portable speaker with 12-hour battery	79.99	Electronics	41	2025-11-18 18:43:09.366441
10	Desk Lamp	LED desk lamp with adjustable brightness and color temperature	34.99	Accessories	88	2025-11-18 18:43:09.366441
\.


--
-- Name: agent_audit_log_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.agent_audit_log_log_id_seq', 1, false);


--
-- Name: agent_run_metrics_metric_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.agent_run_metrics_metric_id_seq', 1, false);


--
-- Name: orders_order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.orders_order_id_seq', 1, false);


--
-- Name: products_product_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.products_product_id_seq', 10, true);


--
-- Name: agent_audit_log agent_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_audit_log
    ADD CONSTRAINT agent_audit_log_pkey PRIMARY KEY (log_id);


--
-- Name: agent_run_metrics agent_run_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_run_metrics
    ADD CONSTRAINT agent_run_metrics_pkey PRIMARY KEY (metric_id);


--
-- Name: agent_run_metrics agent_run_metrics_run_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_run_metrics
    ADD CONSTRAINT agent_run_metrics_run_id_key UNIQUE (run_id);


--
-- Name: customer_context customer_context_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_context
    ADD CONSTRAINT customer_context_pkey PRIMARY KEY (customer_id);


--
-- Name: orders orders_order_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_order_number_key UNIQUE (order_number);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (order_id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (product_id);


--
-- Name: idx_audit_log_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_run_id ON public.agent_audit_log USING btree (run_id);


--
-- Name: idx_audit_log_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_timestamp ON public.agent_audit_log USING btree ("timestamp");


--
-- Name: idx_customer_context_last_interaction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_context_last_interaction ON public.customer_context USING btree (last_interaction_date);


--
-- Name: idx_orders_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_email ON public.orders USING btree (customer_email);


--
-- Name: idx_orders_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_number ON public.orders USING btree (order_number);


--
-- Name: idx_products_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_products_category ON public.products USING btree (category);


--
-- Name: idx_run_metrics_journey; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_run_metrics_journey ON public.agent_run_metrics USING btree (journey_name);


--
-- Name: orders orders_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(product_id);


--
-- PostgreSQL database dump complete
--

\unrestrict EphQ6ovQZUi73YuWJuJV5AGsXyViCS9hVX8HaAXbaWcMgQ2BbhYSSzhoTg7V6yI

