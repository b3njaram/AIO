FROM nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236
# Build contexts may originate from a checkout with umask 077.
COPY --chmod=0644 index.html style.css app.js /usr/share/nginx/html/
COPY --chmod=0644 nginx.conf /etc/nginx/conf.d/default.conf
