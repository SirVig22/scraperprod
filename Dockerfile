FROM fedora:latest
WORKDIR /app

COPY requirements.txt .

RUN dnf install -y \
    cairo-devel gobject-introspection-devel gtk3-devel gcc gcc-c++ redhat-rpm-config python3-devel \
    mosquitto \
    && dnf clean all

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
