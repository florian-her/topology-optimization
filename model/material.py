from __future__ import annotations


class Material:
    def __init__(self, name: str, E: float, yield_strength: float, density: float = 1000.0):
        """Erstellt ein Material mit den wichtigsten Kennwerten.

        Parameters
        ----------
        name : str
            Name des Materials.
        E : float
            E-Modul in GPa.
        yield_strength : float
            Streckgrenze in MPa.
        density : float
            Dichte in kg/m³.
        """
        assert E > 0, "E-Modul muss positiv sein."
        assert yield_strength > 0, "Streckgrenze muss positiv sein."
        assert density > 0, "Dichte muss positiv sein."
        
        self.name = name
        self.E = E
        self.yield_strength = yield_strength
        self.density = density

    @classmethod
    def defaults(cls) -> list[Material]:
        """Gibt die Standardmaterialien zurück.

        Returns
        -------
        list[Material]
            Stahl, Aluminium, Holz (Fichte).
        """
        return [
            cls("Stahl", E=210.0, yield_strength=250.0, density=7850.0),
            cls("Aluminium", E=70.0, yield_strength=270.0, density=2700.0),
            cls("Holz (Fichte)", E=12.0, yield_strength=40.0, density=500.0),
        ]

    def to_dict(self) -> dict:
        """Wandelt das Material in ein Dictionary um für JSON-Serialisierung.

        Returns
        -------
        dict
            Dictionary mit allen Materialwerten.
        """
        return {
            "name": self.name,
            "E": self.E,
            "yield_strength": self.yield_strength,
            "density": self.density,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Material:
        """Erstellt ein Material aus einem Dictionary.

        Parameters
        ----------
        d : dict
            Dictionary mit den Materialwerten.

        Returns
        -------
        Material
            Das wiederhergestellte Material.
        """
        return cls(
            name=d["name"],
            E=float(d["E"]),
            yield_strength=float(d["yield_strength"]),
            density=float(d.get("density", 1000.0)),
        )

    def __str__(self) -> str:
        return (f"Material({self.name}, E={self.E} GPa, "
                f"σ_y={self.yield_strength} MPa, ρ={self.density} kg/m³)")

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    for m in Material.defaults():
        print(m)

    custom = Material("Titan", E=115.0, yield_strength=880.0, density=4500.0)
    print(custom)
    d = custom.to_dict()
    m2 = Material.from_dict(d)
    assert m2.name == custom.name
    assert m2.E == custom.E
    print("Serialisierung OK.")