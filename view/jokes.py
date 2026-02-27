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
    (
        'Ein Informatiker schiebt einen Kinderwagen durch den Park. '
        'Kommt ein älteres Ehepaar: "Junge oder Mädchen?" '
        'Informatiker: "Richtig!"'
    ),
    (
        "Warum klebt auf allen Intel-Rechnern \"Intel inside\"? "
        "Ein Warnhinweis ist einfach nötig."
    ),
    (
        "Wenn Baumeister Gebäude so bauten, wie Programmierer Programme entwickeln, "
        "dann würde der erste Specht, der vorbeikäme, die Zivilisation zerstören!!!"
    ),
    (
        "Ein Informatiker verliert nie seine Arbeit. Er hat ein Backup. "
        "Zwei, um genau zu sein. Ok, drei, verteilt auf vier Festplatten. "
        "Eine davon ist in der Cloud."
    ),
    (
        "Ein Informatiker ist jemand, der die Lösung eines Problems versteht, "
        "aber nicht das Problem."
    ),
    (
        "Was ist der Unterschied zwischen einem Informatiker und einem Physiker? "
        "Der Physiker glaubt, ein Kilobyte sind 1000 Byte. "
        "Der Informatiker glaubt, ein Kilometer sind 1024 Meter."
    ),
    (
        'Anruf bei einer Hotline:\n'
        'Anrufer: "Ich benutze Windows …"\n'
        'Hotline: "Ja …?"\n'
        'Kunde: "Mein Computer funktioniert nicht richtig."\n'
        'Hotline: "Das sagten Sie bereits."'
    ),
    "Wie nennt man 8 Hobits? 1 Hobyte.",
    (
        "Ein Informatiker stellt sich jeden Abend ein volles und ein leeres Glas Wasser "
        "neben sein Bett. Warum? – Das volle Glas hat er, falls er in der Nacht aufwacht "
        "und Durst hat. Und das leere Glas, falls er in der Nacht aufwacht und keinen "
        "Durst hat."
    ),
    (
        'Sohn zu seinem Vater: "Papa, schreibt man Adresse mit einem oder zwei s?" '
        'Der Vater (Informatiker): "Schreib einfach URL und lass mich weiter arbeiten."'
    ),
]


def get_shuffled_jokes() -> list[str]:
    """Gibt alle Witze in zufälliger Reihenfolge zurück."""
    jokes = _JOKES.copy()
    random.shuffle(jokes)
    return jokes
