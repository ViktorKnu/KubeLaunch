FROM nginx:1.29-alpine

COPY nginx-main.conf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY src /usr/share/nginx/html

RUN chown -R nginx:nginx /etc/nginx /usr/share/nginx/html

USER nginx

EXPOSE 8080
