To just run db in docker run this command:</br>
`docker run --name postgresql -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:12`

Else run the docker-compose command inside app folder:</br>
`docker-compose up -d`

After all table are created add data to Roles table:</br>
`INSERT INTO public.roles (id, name) VALUES (1, 'USER');
INSERT INTO public.roles (id, name) VALUES (2, 'ADMIN');`
