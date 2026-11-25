FROM python:3.13-alpine
WORKDIR /app
COPY --chmod=0644 server.py index.html /app/
USER 65534:65534
EXPOSE 8080
CMD ["python","-B","/app/server.py"]
