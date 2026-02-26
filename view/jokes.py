import random


_JOKES = [
    (
        "Hardware ist das, was nach 10 Jahren kaputtgeht. "
        "Software ist das, was von Anfang an nicht funktioniert. "
        "Mechatronik ist die Meisterdisziplin, beides so zu kombinieren, "
        "dass es von Anfang an nicht funktioniert und trotzdem nach 10 Jahren kaputtgeht."
    ),
    (
        "Ein Maschinenbauer, ein Elektrotechniker und ein Informatiker stehen "
        "mit einem kaputten Auto am Straßenrand.\n"
        'Maschinenbauer: "Das ist sicher die Zylinderkopfdichtung!"\n'
        'Elektrotechniker: "Nein, das muss die Lichtmaschine sein!"\n'
        'Informatiker: "Leute, wir steigen jetzt alle einfach mal aus und wieder ein, '
        'vielleicht geht\'s dann wieder."\n'
        "Da kommt ein Mechatroniker vorbei, schließt seinen Laptop ans Auto an, "
        'tippt ein bisschen und sagt: "Es ist ein mechanischer Totalschaden, aber ich habe '
        'einfach die Fehlertoleranzen in der Software hochgesetzt. Wir können weiterfahren."'
    ),
    (
        '"Oh, du studierst Mechatronik? Cool, kannst du meine Waschmaschine reparieren?"\n'
        '"Ich programmiere eigentlich KI-gestützte 6-Achs-Industrieroboter für die '
        'Automobilfertigung... aber ja, gib her, wahrscheinlich ist nur das Flusensieb voll."'
    ),
    (
        "Was haben ein Sternekoch aus Neapel und ein Mechatroniker-Azubi im ersten Lehrjahr "
        "gemeinsam? Beide sind absolute Meister, wenn es darum geht, perfekten Spaghetti-Code "
        "zu schreiben und Kabelsalat im Schaltschrank zu produzieren."
    ),
    (
        "Es gibt genau 10 Arten von Menschen auf der Welt. "
        "Die, die Binärcode verstehen, und die, die ihn nicht verstehen."
    ),
    (
        "Ein Software-Tester geht in eine Bar. Er bestellt ein Bier. "
        "Er bestellt 0 Bier. Er bestellt 999999999 Bier. Er bestellt ein Krokodil. "
        "Er bestellt -1 Bier. Ein echter Kunde betritt die Bar und fragt, wo die Toilette ist. "
        "Die Bar explodiert."
    ),
    (
        'Die Frau sagt zu ihrem Mann (einem Programmierer): "Geh bitte in den Supermarkt '
        'und kauf eine Flasche Milch. Und wenn sie Eier haben, bring 6 mit."\n'
        "Der Mann kommt mit 6 Flaschen Milch zurück.\n"
        'Die Frau fragt: "Warum hast du 6 Flaschen Milch gekauft?!"\n'
        'Er antwortet: "Sie hatten Eier."'
    ),
    (
        "Was ist der Unterschied zwischen Hardware und Software? "
        "Hardware ist das, worauf man einschlägt, wenn die Software abstürzt."
    ),
    (
        "Wo verstecken Informatiker am liebsten eine Leiche? "
        "Auf Seite 2 der Google-Suchergebnisse. Da schaut ohnehin nie jemand nach."
    ),
    (
        "Die Geburt: Was sind die ersten Worte eines Informatikers, wenn er geboren wird? "
        '"Hello World!"'
    ),
]


def get_shuffled_jokes() -> list[str]:
    """Gibt alle Witze in zufälliger Reihenfolge zurück."""
    jokes = _JOKES.copy()
    random.shuffle(jokes)
    return jokes
