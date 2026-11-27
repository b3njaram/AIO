FROM nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236
# Build contexts may originate from a checkout with umask 077.
COPY --chmod=0644 index.html style.css app.js /usr/share/nginx/html/
COPY --chmod=0644 nginx.conf /etc/nginx/nginx.conf
USER nginx
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["wget","-q","-T","3","-O","/dev/null","http://127.0.0.1:8080/"]
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
