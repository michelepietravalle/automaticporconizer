import random
import socket
import ipaddress
from pathlib import Path

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

PREGHIERINE_FILE = Path("preghierine.txt")


def load_phrases():
    """Carica le frasi da preghierine.txt, ignorando le righe vuote."""
    if not PREGHIERINE_FILE.exists():
        raise FileNotFoundError(f"File non trovato: {PREGHIERINE_FILE}")
    lines = PREGHIERINE_FILE.read_text(encoding="utf-8").splitlines()
    phrases = [l.strip() for l in lines if l.strip()]
    if not phrases:
        raise ValueError("Il file preghierine.txt è vuoto o contiene solo righe vuote.")
    return phrases


def pick_random_phrase():
    phrases = load_phrases()
    return random.choice(phrases)


def pick_random_ip(subnet_cidr: str) -> str:
    """
    Restituisce un IP casuale dalla subnet CIDR (es. '192.168.1.0/24').
    """
    network = ipaddress.ip_network(subnet_cidr, strict=False)
    hosts = list(network.hosts()) or list(network)
    return str(random.choice(hosts))


def pick_random_port(min_port: int, max_port: int) -> int:
    if not (0 < min_port <= 65535 and 0 < max_port <= 65535):
        raise ValueError("Le porte devono essere tra 1 e 65535.")
    if min_port > max_port:
        raise ValueError("min_port deve essere <= max_port.")
    return random.randint(min_port, max_port)


def send_udp_message(message: str, host: str, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(message.encode("utf-8"), (host, port))
    finally:
        sock.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/send-random", methods=["POST"])
def api_send_random():
    """
    Corpo JSON atteso:
    {
      "subnet": "192.168.1.0",
      "cidr": 24,
      "minPort": 1024,
      "maxPort": 65535
    }
    """
    data = request.get_json(silent=True) or {}

    subnet = data.get("subnet", "").strip()
    cidr = data.get("cidr")
    min_port = data.get("minPort", 1024)
    max_port = data.get("maxPort", 65535)

    if not subnet:
        return jsonify({"error": "Campo 'subnet' mancante."}), 400
    if cidr is None:
        return jsonify({"error": "Campo 'cidr' mancante."}), 400

    try:
        subnet_cidr = f"{subnet}/{int(cidr)}"
    except (TypeError, ValueError):
        return jsonify({"error": "CIDR non valido."}), 400

    try:
        target_ip = pick_random_ip(subnet_cidr)
        target_port = pick_random_port(int(min_port), int(max_port))
        phrase = pick_random_phrase()

        send_udp_message(phrase, target_ip, target_port)

        return jsonify(
            {
                "status": "ok",
                "messageSent": phrase,
                "targetIp": target_ip,
                "targetPort": target_port,
                "subnetCidr": subnet_cidr,
            }
        )
    except (FileNotFoundError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except OSError as e:
        return jsonify({"error": f"Errore di rete/UDP: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
