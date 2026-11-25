FROM python:3.13-alpine@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e
WORKDIR /app
COPY --chmod=0644 server.py index.html /app/
USER 65534:65534
EXPOSE 8080
CMD ["python","-B","/app/server.py"]
