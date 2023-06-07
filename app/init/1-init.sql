-- Create the database
CREATE DATABASE assignment;

-- Connect to the newly created database
\c assignment;

-- Create a table
create table roles
(
    id   serial      not null
        constraint roles_pkey
            primary key,
    name varchar(50) not null
        constraint roles_name_key
            unique
);

alter table roles
    owner to postgres;

-- insert roles to roles table
INSERT INTO public.roles (id, name)
VALUES (1, 'USER');
INSERT INTO public.roles (id, name)
VALUES (2, 'ADMIN');