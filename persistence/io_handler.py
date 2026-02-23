import json
import io

import matplotlib.pyplot as plt

from model.structure import Structure


class IOHandler:
    """Speichert und lädt Strukturen als JSON; exportiert Plots als PNG."""

    VERSION = 1

    @staticmethod
    def save(structure: Structure, filepath: str) -> None:
        """Speichert die Struktur in eine JSON-Datei.

        Speichert Gitterdimensionen, alle Knoten (inkl. Randbedingungen,
        Kräfte, aktiv-Status) und alle Federn (inkl. aktiv-Status, k falls
        manuell gesetzt).

        Parameters
        ----------
        structure : Structure
            Die zu speichernde Struktur.
        filepath : str
            Ziel-Dateipfad (z.B. "struktur.json").
        """
        nodes_data = [
            {
                "id": n.id,
                "x": n.x,
                "y": n.y,
                "active": n.active,
                "fix_x": n.fix_x,
                "fix_y": n.fix_y,
                "force_x": n.force_x,
                "force_y": n.force_y,
            }
            for n in structure.nodes
        ]

        springs_data = [
            {
                "id": s.id,
                "node_a": s.node_a.id,
                "node_b": s.node_b.id,
                "k": s.k,
                "active": s.active,
            }
            for s in structure.springs
        ]

        data = {
            "version": IOHandler.VERSION,
            "width": structure.width,
            "height": structure.height,
            "nodes": nodes_data,
            "springs": springs_data,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load(filepath: str) -> Structure:
        """Lädt eine Struktur aus einer JSON-Datei.

        Erstellt zunächst ein neues Gitter mit den gespeicherten Maßen,
        überschreibt dann alle Knoten- und Federeigenschaften aus dem JSON.

        Parameters
        ----------
        filepath : str
            Quell-Dateipfad.

        Returns
        -------
        Structure
            Wiederhergestellte Struktur.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("version") == IOHandler.VERSION, (
            f"Unbekannte Dateiversion: {data.get('version')}"
        )

        structure = Structure(data["width"], data["height"])

        node_by_id = {n.id: n for n in structure.nodes}
        for nd in data["nodes"]:
            n = node_by_id[nd["id"]]
            n.active = nd["active"]
            n.fix_x = nd["fix_x"]
            n.fix_y = nd["fix_y"]
            n.force_x = nd["force_x"]
            n.force_y = nd["force_y"]

        spring_by_id = {s.id: s for s in structure.springs}
        for sd in data["springs"]:
            s = spring_by_id[sd["id"]]
            s.k = sd["k"]
            s.active = sd["active"]

        return structure

    @staticmethod
    def to_png_bytes(fig: plt.Figure) -> bytes:
        """Exportiert eine Matplotlib-Figur als PNG-Bytes.

        Geeignet für Streamlit-Download-Buttons:
            st.download_button("Download", IOHandler.to_png_bytes(fig), "plot.png", "image/png")

        Parameters
        ----------
        fig : plt.Figure
            Die zu exportierende Figur.

        Returns
        -------
        bytes
            PNG-Bilddaten.
        """
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        return buf.read()

    @staticmethod
    def load_from_bytes(data: bytes) -> Structure:
        """Lädt eine Struktur aus JSON-Bytes.

        Parameters
        ----------
        data : bytes
            UTF-8-kodierte JSON-Bytes.

        Returns
        -------
        Structure
            Wiederhergestellte Struktur.
        """
        raw = json.loads(data.decode("utf-8"))

        assert raw.get("version") == IOHandler.VERSION, (
            f"Unbekannte Dateiversion: {raw.get('version')}"
        )

        structure = Structure(raw["width"], raw["height"])

        node_by_id = {n.id: n for n in structure.nodes}
        for nd in raw["nodes"]:
            n = node_by_id[nd["id"]]
            n.active = nd["active"]
            n.fix_x = nd["fix_x"]
            n.fix_y = nd["fix_y"]
            n.force_x = nd["force_x"]
            n.force_y = nd["force_y"]

        spring_by_id = {s.id: s for s in structure.springs}
        for sd in raw["springs"]:
            s = spring_by_id[sd["id"]]
            s.k = sd["k"]
            s.active = sd["active"]

        return structure

    @staticmethod
    def to_json_bytes(structure: Structure) -> bytes:
        """Serialisiert eine Struktur als JSON-Bytes.

        Geeignet für Streamlit-Download-Buttons:
            st.download_button("Download", IOHandler.to_json_bytes(s), "struktur.json", "application/json")

        Parameters
        ----------
        structure : Structure
            Die zu serialisierende Struktur.

        Returns
        -------
        bytes
            UTF-8-kodierte JSON-Bytes.
        """
        nodes_data = [
            {
                "id": n.id,
                "x": n.x,
                "y": n.y,
                "active": n.active,
                "fix_x": n.fix_x,
                "fix_y": n.fix_y,
                "force_x": n.force_x,
                "force_y": n.force_y,
            }
            for n in structure.nodes
        ]

        springs_data = [
            {
                "id": s.id,
                "node_a": s.node_a.id,
                "node_b": s.node_b.id,
                "k": s.k,
                "active": s.active,
            }
            for s in structure.springs
        ]

        data = {
            "version": IOHandler.VERSION,
            "width": structure.width,
            "height": structure.height,
            "nodes": nodes_data,
            "springs": springs_data,
        }

        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


if __name__ == "__main__":
    import tempfile
    import os

    from model.structure import Structure

    print("=" * 60)
    print("IOHandler Test: Speichern und Laden")
    print("=" * 60)

    s = Structure(4, 3)
    s.nodes[0].fix_x = 1
    s.nodes[0].fix_y = 1
    s.nodes[s._node_id(3, 2)].fix_y = 1
    s.nodes[s._node_id(2, 2)].force_y = -0.5
    s.remove_node(5)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        path = tf.name

    try:
        IOHandler.save(s, path)
        print(f"Gespeichert: {path}")

        s2 = IOHandler.load(path)
        print(f"Geladen: {s2}")
        print(f"Knoten aktiv: {s2.active_node_count()} / {len(s2.nodes)}")
        print(f"Federn aktiv: {s2.active_spring_count()} / {len(s2.springs)}")

        assert s2.active_node_count() == s.active_node_count()
        assert s2.active_spring_count() == s.active_spring_count()
        assert s2.nodes[0].fix_x == 1
        assert s2.nodes[0].fix_y == 1
        assert not s2.nodes[5].active
        print("Alle Assertions bestanden.")
    finally:
        os.unlink(path)

    png = IOHandler.to_png_bytes(plt.figure())
    print(f"PNG-Bytes: {len(png)} bytes")
    plt.close("all")

    json_bytes = IOHandler.to_json_bytes(s)
    print(f"JSON-Bytes: {len(json_bytes)} bytes")
    print("=" * 60)
