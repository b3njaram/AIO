FROM nginx:1.28-alpine
# Build contexts may originate from a checkout with umask 077.
COPY --chmod=0644 index.html style.css app.js /usr/share/nginx/html/
COPY --chmod=0644 nginx.conf /etc/nginx/conf.d/default.conf
