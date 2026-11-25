"""Traditional prayers, the Holy Rosary and an examination of conscience (Latin + English).

All texts are the traditional, public-domain forms used before 1962.
"""
import datetime as dt

from . import liturgy

# key: (English title, Latin title, English text, Latin text or None, category)
# "℣." / "℟." mark versicles and responses; "|" separates paragraphs.
PRAYERS = {
    "signum": ("Sign of the Cross", "Signum Crucis",
               "In the name of the Father, and of the Son, and of the Holy Ghost. Amen.",
               "In nómine Patris, et Fílii, et Spíritus Sancti. Amen.", "essential"),
    "pater": ("Our Father", "Pater Noster",
              "Our Father, who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on "
              "earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we "
              "forgive those who trespass against us; and lead us not into temptation, but deliver us from "
              "evil. Amen.",
              "Pater noster, qui es in cælis, sanctificétur nomen tuum. Advéniat regnum tuum. Fiat volúntas "
              "tua, sicut in cælo et in terra. Panem nostrum quotidiánum da nobis hódie, et dimítte nobis "
              "débita nostra, sicut et nos dimíttimus debitóribus nostris. Et ne nos indúcas in tentatiónem, "
              "sed líbera nos a malo. Amen.", "essential"),
    "ave": ("Hail Mary", "Ave Maria",
            "Hail Mary, full of grace, the Lord is with thee; blessed art thou among women, and blessed is the "
            "fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of "
            "our death. Amen.",
            "Ave María, grátia plena, Dóminus tecum. Benedícta tu in muliéribus, et benedíctus fructus "
            "ventris tui, Iesus. Sancta María, Mater Dei, ora pro nobis peccatóribus, nunc et in hora mortis "
            "nostræ. Amen.", "essential"),
    "gloria": ("Glory Be", "Gloria Patri",
               "Glory be to the Father, and to the Son, and to the Holy Ghost. As it was in the beginning, is "
               "now, and ever shall be, world without end. Amen.",
               "Glória Patri, et Fílio, et Spirítui Sancto. Sicut erat in princípio, et nunc, et semper, et in "
               "sǽcula sæculórum. Amen.", "essential"),
    "credo": ("Apostles' Creed", "Symbolum Apostolorum",
              "I believe in God, the Father Almighty, Creator of heaven and earth; and in Jesus Christ, His only "
              "Son, our Lord; who was conceived by the Holy Ghost, born of the Virgin Mary, suffered under "
              "Pontius Pilate, was crucified, died, and was buried. He descended into hell; the third day He "
              "rose again from the dead; He ascended into heaven, and sitteth at the right hand of God, the "
              "Father Almighty; from thence He shall come to judge the living and the dead. I believe in the "
              "Holy Ghost, the holy Catholic Church, the communion of saints, the forgiveness of sins, the "
              "resurrection of the body, and life everlasting. Amen.",
              "Credo in Deum, Patrem omnipoténtem, Creatórem cæli et terræ. Et in Iesum Christum, Fílium eius "
              "únicum, Dóminum nostrum: qui concéptus est de Spíritu Sancto, natus ex María Vírgine, passus "
              "sub Póntio Piláto, crucifíxus, mórtuus, et sepúltus: descéndit ad ínferos; tértia die resurréxit "
              "a mórtuis; ascéndit ad cælos; sedet ad déxteram Dei Patris omnipoténtis: inde ventúrus est "
              "iudicáre vivos et mórtuos. Credo in Spíritum Sanctum, sanctam Ecclésiam cathólicam, Sanctórum "
              "communiónem, remissiónem peccatórum, carnis resurrectiónem, vitam ætérnam. Amen.", "essential"),
    "fatima": ("O My Jesus (Fatima Prayer)", "O mi Iesu",
               "O my Jesus, forgive us our sins, save us from the fires of hell; lead all souls to Heaven, "
               "especially those who are in most need of Thy mercy.",
               "O mi Iesu, dimítte nobis débita nostra, líbera nos ab igne inférni, conduc in cælum omnes "
               "ánimas, præsértim illas quæ máxime índigent misericórdia tua.", "marian"),
    "salve": ("Hail, Holy Queen", "Salve Regina",
              "Hail, holy Queen, Mother of mercy, our life, our sweetness, and our hope. To thee do we cry, poor "
              "banished children of Eve; to thee do we send up our sighs, mourning and weeping in this vale of "
              "tears. Turn, then, most gracious advocate, thine eyes of mercy toward us; and after this our "
              "exile show unto us the blessed fruit of thy womb, Jesus. O clement, O loving, O sweet Virgin "
              "Mary.|℣. Pray for us, O holy Mother of God.|℟. That we may be made worthy of the promises of "
              "Christ.",
              "Salve, Regína, Mater misericórdiæ, vita, dulcédo, et spes nostra, salve. Ad te clamámus, éxsules "
              "fílii Hevæ. Ad te suspirámus, geméntes et flentes in hac lacrimárum valle. Eia, ergo, advocáta "
              "nostra, illos tuos misericórdes óculos ad nos convérte. Et Iesum, benedíctum fructum ventris "
              "tui, nobis post hoc exsílium osténde. O clemens, O pia, O dulcis Virgo María.|℣. Ora pro nobis, "
              "sancta Dei Génetrix.|℟. Ut digni efficiámur promissiónibus Christi.", "marian"),
    "rosary_oratio": ("Prayer after the Rosary", "Oratio post Rosarium",
                      "Let us pray. O God, whose only-begotten Son, by His life, death, and resurrection, has "
                      "purchased for us the rewards of eternal life: grant, we beseech Thee, that meditating upon "
                      "these mysteries of the most holy Rosary of the Blessed Virgin Mary, we may imitate what "
                      "they contain and obtain what they promise. Through the same Christ our Lord. Amen.",
                      "Orémus. Deus, cuius Unigénitus per vitam, mortem et resurrectiónem suam nobis salútis "
                      "ætérnæ prǽmia comparávit: concéde, quǽsumus; ut hæc mystéria sacratíssimo beátæ Maríæ "
                      "Vírginis Rosário recoléntes, et imitémur quod cóntinent, et quod promíttunt assequámur. "
                      "Per eúndem Christum Dóminum nostrum. Amen.", "marian"),
    "angelus": ("The Angelus", "Angelus Domini",
                "℣. The Angel of the Lord declared unto Mary.|℟. And she conceived of the Holy Ghost.|Hail Mary…|"
                "℣. Behold the handmaid of the Lord.|℟. Be it done unto me according to thy word.|Hail Mary…|"
                "℣. And the Word was made flesh.|℟. And dwelt among us.|Hail Mary…|"
                "℣. Pray for us, O holy Mother of God.|℟. That we may be made worthy of the promises of Christ.|"
                "Let us pray. Pour forth, we beseech Thee, O Lord, Thy grace into our hearts; that we, to whom "
                "the Incarnation of Christ Thy Son was made known by the message of an Angel, may by His Passion "
                "and Cross be brought to the glory of His Resurrection. Through the same Christ our Lord. Amen.",
                "℣. Angelus Dómini nuntiávit Maríæ.|℟. Et concépit de Spíritu Sancto.|Ave María…|"
                "℣. Ecce ancílla Dómini.|℟. Fiat mihi secúndum verbum tuum.|Ave María…|"
                "℣. Et Verbum caro factum est.|℟. Et habitávit in nobis.|Ave María…|"
                "℣. Ora pro nobis, sancta Dei Génetrix.|℟. Ut digni efficiámur promissiónibus Christi.|"
                "Orémus. Grátiam tuam, quǽsumus, Dómine, méntibus nostris infúnde; ut qui, Angelo nuntiánte, "
                "Christi Fílii tui incarnatiónem cognóvimus, per passiónem eius et crucem ad resurrectiónis "
                "glóriam perducámur. Per eúndem Christum Dóminum nostrum. Amen.", "marian"),
    "regina": ("Queen of Heaven (Eastertide)", "Regina Cæli",
               "Queen of Heaven, rejoice, alleluia. For He whom thou didst merit to bear, alleluia. Hath risen, "
               "as He said, alleluia. Pray for us to God, alleluia.|℣. Rejoice and be glad, O Virgin Mary, "
               "alleluia.|℟. For the Lord hath risen indeed, alleluia.|Let us pray. O God, who gavest joy to the "
               "world through the resurrection of Thy Son, our Lord Jesus Christ, grant, we beseech Thee, that "
               "through His Mother, the Virgin Mary, we may obtain the joys of everlasting life. Through the "
               "same Christ our Lord. Amen.",
               "Regína cæli, lætáre, allelúia. Quia quem meruísti portáre, allelúia. Resurréxit, sicut dixit, "
               "allelúia. Ora pro nobis Deum, allelúia.|℣. Gaude et lætáre, Virgo María, allelúia.|℟. Quia "
               "surréxit Dóminus vere, allelúia.|Orémus. Deus, qui per resurrectiónem Fílii tui, Dómini nostri "
               "Iesu Christi, mundum lætificáre dignátus es: præsta, quǽsumus; ut per eius Genetrícem Vírginem "
               "Maríam, perpétuæ capiámus gáudia vitæ. Per eúndem Christum Dóminum nostrum. Amen.", "marian"),
    "memorare": ("The Memorare", "Memorare",
                 "Remember, O most gracious Virgin Mary, that never was it known that anyone who fled to thy "
                 "protection, implored thy help, or sought thy intercession was left unaided. Inspired with this "
                 "confidence, I fly unto thee, O Virgin of virgins, my Mother; to thee do I come; before thee I "
                 "stand, sinful and sorrowful. O Mother of the Word Incarnate, despise not my petitions, but in "
                 "thy mercy hear and answer me. Amen.",
                 "Memoráre, o piíssima Virgo María, non esse audítum a sǽculo, quemquam ad tua curréntem "
                 "præsídia, tua implorántem auxília, tua peténtem suffrágia, esse derelíctum. Ego tali animátus "
                 "confidéntia, ad te, Virgo Vírginum, Mater, curro, ad te vénio, coram te gemens peccátor "
                 "assísto. Noli, Mater Verbi, verba mea despícere; sed áudi propítia et exáudi. Amen.", "marian"),
    "sub_tuum": ("We Fly to Thy Patronage", "Sub tuum præsidium",
                 "We fly to thy patronage, O holy Mother of God; despise not our petitions in our necessities, "
                 "but deliver us always from all dangers, O glorious and blessed Virgin. Amen.",
                 "Sub tuum præsídium confúgimus, sancta Dei Génetrix: nostras deprecatiónes ne despícias in "
                 "necessitátibus: sed a perículis cunctis líbera nos semper, Virgo gloriósa et benedícta. Amen.",
                 "marian"),
    "michael": ("Prayer to St. Michael", "Ad Sanctum Michaëlem",
                "Saint Michael the Archangel, defend us in battle; be our safeguard against the wickedness and "
                "snares of the devil. May God rebuke him, we humbly pray; and do thou, O Prince of the heavenly "
                "host, by the power of God, thrust into hell Satan and all the evil spirits who prowl about the "
                "world seeking the ruin of souls. Amen.",
                "Sancte Míchaël Archángele, defénde nos in prǽlio; contra nequítiam et insídias diáboli esto "
                "præsídium. Ímperet illi Deus, súpplices deprecámur: tuque, Princeps milítiæ cæléstis, Sátanam "
                "aliósque spíritus malígnos, qui ad perditiónem animárum pervagántur in mundo, divína virtúte in "
                "inférnum detrúde. Amen.", "saints"),
    "angele_dei": ("Prayer to the Guardian Angel", "Angele Dei",
                   "Angel of God, my guardian dear, to whom God's love commits me here, ever this day be at my "
                   "side, to light and guard, to rule and guide. Amen.",
                   "Ángele Dei, qui custos es mei, me, tibi commíssum pietáte supérna, hódie illúmina, custódi, "
                   "rege, et gubérna. Amen.", "saints"),
    "veni_sancte": ("Come, Holy Ghost", "Veni, Sancte Spiritus",
                    "Come, O Holy Ghost, fill the hearts of Thy faithful and kindle in them the fire of Thy "
                    "love.|℣. Send forth Thy Spirit and they shall be created.|℟. And Thou shalt renew the face of "
                    "the earth.|Let us pray. O God, who didst instruct the hearts of the faithful by the light of "
                    "the Holy Ghost, grant us in the same Spirit to be truly wise and ever to rejoice in His "
                    "consolation. Through Christ our Lord. Amen.",
                    "Veni, Sancte Spíritus, reple tuórum corda fidélium, et tui amóris in eis ignem accénde.|"
                    "℣. Emítte Spíritum tuum et creabúntur.|℟. Et renovábis fáciem terræ.|Orémus. Deus, qui corda "
                    "fidélium Sancti Spíritus illustratióne docuísti: da nobis in eódem Spíritu recta sápere, et "
                    "de eius semper consolatióne gaudére. Per Christum Dóminum nostrum. Amen.", "daily"),
    "anima": ("Soul of Christ", "Anima Christi",
              "Soul of Christ, sanctify me. Body of Christ, save me. Blood of Christ, inebriate me. Water from the "
              "side of Christ, wash me. Passion of Christ, strengthen me. O good Jesus, hear me. Within Thy "
              "wounds hide me. Suffer me not to be separated from Thee. From the malicious enemy defend me. In "
              "the hour of my death call me, and bid me come to Thee, that with Thy saints I may praise Thee for "
              "ever and ever. Amen.",
              "Ánima Christi, sanctífica me. Corpus Christi, salva me. Sanguis Christi, inébria me. Aqua láteris "
              "Christi, lava me. Pássio Christi, confórta me. O bone Iesu, exáudi me. Intra tua vúlnera "
              "abscónde me. Ne permíttas me separári a te. Ab hoste malígno defénde me. In hora mortis meæ voca "
              "me. Et iube me veníre ad te, ut cum Sanctis tuis laudem te in sǽcula sæculórum. Amen.", "mass"),
    "en_ego": ("Prayer before a Crucifix", "En ego, o bone et dulcissime Iesu",
               "Behold, O good and most sweet Jesus, I cast myself upon my knees in Thy sight, and with the most "
               "fervent desire of my soul I pray and beseech Thee that Thou wouldst impress upon my heart lively "
               "sentiments of faith, hope and charity, with true repentance for my sins and a firm purpose of "
               "amendment, while with deep affection and grief of soul I ponder within myself and mentally "
               "contemplate Thy five most precious wounds, having before my eyes that which David the prophet "
               "put in Thy mouth concerning Thee, O good Jesus: They have pierced My hands and My feet; they "
               "have numbered all My bones.",
               "En ego, o bone et dulcíssime Iesu, ante conspéctum tuum génibus me provólvo, ac máximo ánimi "
               "ardóre te oro atque obtéstor, ut meum in cor vívidos fídei, spei et caritátis sensus, atque "
               "veram peccatórum meórum pæniténtiam, eáque emendándi firmíssimam voluntátem velis imprímere; dum "
               "magno ánimi afféctu et dolóre tua quinque vúlnera mecum ipse consídero ac mente contémplor, "
               "illud præ óculis habens, quod iam in ore ponébat tuo David prophéta de te, o bone Iesu: "
               "Fodérunt manus meas et pedes meos: dinumeravérunt ómnia ossa mea.", "mass"),
    "contritio": ("Act of Contrition", "Actus Contritionis",
                  "O my God, I am heartily sorry for having offended Thee, and I detest all my sins because of "
                  "Thy just punishments, but most of all because they offend Thee, my God, who art all-good and "
                  "deserving of all my love. I firmly resolve, with the help of Thy grace, to sin no more and to "
                  "avoid the near occasions of sin. Amen.",
                  "Deus meus, ex toto corde pǽnitet me ómnium meórum peccatórum, éaque detéstor, quia peccándo, "
                  "non solum pœnas a te iuste statútas proméritus sum, sed præsértim quia offéndi te, summum "
                  "bonum, ac dignum qui super ómnia diligáris. Ídeo fírmiter propóno, adiuvánte grátia tua, de "
                  "cétero me non peccatúrum peccandíque occasiónes próximas fugitúrum. Amen.", "acts"),
    "fides": ("Act of Faith", "Actus Fidei",
              "O my God, I firmly believe that Thou art one God in three Divine Persons, Father, Son, and Holy "
              "Ghost; I believe that Thy Divine Son became man and died for our sins, and that He will come to "
              "judge the living and the dead. I believe these and all the truths which the holy Catholic Church "
              "teaches, because Thou hast revealed them, who canst neither deceive nor be deceived. Amen.",
              "Dómine Deus, firma fide credo et confíteor ómnia et síngula quæ sancta Ecclésia Cathólica "
              "propónit, quia tu ea ómnia, Deus, revelásti, qui es ætérna véritas et sapiéntia quæ nec fállere "
              "nec falli potest. In hac fide vívere et mori státuo. Amen.", "acts"),
    "spes": ("Act of Hope", "Actus Spei",
             "O my God, relying on Thy infinite goodness and promises, I hope to obtain pardon of my sins, the "
             "help of Thy grace, and life everlasting, through the merits of Jesus Christ, my Lord and Redeemer. "
             "Amen.",
             "Dómine Deus, spero per grátiam tuam remissiónem ómnium peccatórum, et post hanc vitam ætérnam "
             "felicitátem me esse consecutúrum: quia tu promisísti, qui es infiníte potens, fidélis, benígnus, "
             "et miséricors. In hac spe vívere et mori státuo. Amen.", "acts"),
    "caritas": ("Act of Charity", "Actus Caritatis",
                "O my God, I love Thee above all things, with my whole heart and soul, because Thou art all-good "
                "and worthy of all love. I love my neighbor as myself for the love of Thee. I forgive all who "
                "have injured me, and ask pardon of all whom I have injured. Amen.",
                "Dómine Deus, amo te super ómnia et próximum meum propter te, quia tu es summum, infinítum, et "
                "perfectíssimum bonum, omni dilectióne dignum. In hac caritáte vívere et mori státuo. Amen.",
                "acts"),
    "oblatio": ("Morning Offering", "Oblatio matutina",
                "O Jesus, through the Immaculate Heart of Mary, I offer Thee my prayers, works, joys and "
                "sufferings of this day for all the intentions of Thy Sacred Heart, in union with the Holy "
                "Sacrifice of the Mass throughout the world, in reparation for my sins, for the intentions of all "
                "our associates, and in particular for the intentions of the Holy Father. Amen.", None, "daily"),
    "benedic": ("Grace before Meals", "Benedictio mensæ",
                "Bless us, O Lord, and these Thy gifts, which we are about to receive from Thy bounty, through "
                "Christ our Lord. Amen.",
                "Bénedic, Dómine, nos et hæc tua dona, quæ de tua largitáte sumus sumptúri. Per Christum "
                "Dóminum nostrum. Amen.", "daily"),
    "agimus": ("Grace after Meals", "Gratiarum actio",
               "We give Thee thanks, Almighty God, for all Thy benefits, who livest and reignest for ever and "
               "ever. Amen.",
               "Ágimus tibi grátias, omnípotens Deus, pro univérsis benefíciis tuis, qui vivis et regnas in "
               "sǽcula sæculórum. Amen.", "daily"),
    "requiem": ("Eternal Rest (for the Dead)", "Requiem æternam",
                "Eternal rest grant unto them, O Lord, and let perpetual light shine upon them. May they rest in "
                "peace. Amen.",
                "Réquiem ætérnam dona eis, Dómine, et lux perpétua lúceat eis. Requiéscant in pace. Amen.",
                "daily"),
}

CATEGORIES = [  # key, English, Latin
    ("essential", "Essential prayers", "Preces fundamentales"),
    ("daily", "Daily prayers", "Preces quotidianæ"),
    ("marian", "To Our Lady", "Ad Beatam Mariam Virginem"),
    ("saints", "To the Angels and Saints", "Ad Angelos et Sanctos"),
    ("acts", "Acts of the Theological Virtues and of Contrition", "Actus virtutum theologicarum"),
    ("mass", "Before and after Holy Communion", "Ante et post Communionem"),
]

# ------------------------------------------------------------------ Rosary (fifteen mysteries)
# set key: (English, Latin, [(English, Latin, fruit EN, fruit LA, Scripture)])
MYSTERIES = {
    "joyful": ("The Joyful Mysteries", "Mysteria Gaudiosa", [
        ("The Annunciation", "Annuntiatio", "Humility", "Humilitas", "Luke 1:26-38"),
        ("The Visitation", "Visitatio", "Love of neighbor", "Caritas erga proximum", "Luke 1:39-56"),
        ("The Nativity", "Nativitas Domini", "Poverty of spirit", "Paupertas spiritus", "Luke 2:1-20"),
        ("The Presentation in the Temple", "Præsentatio in Templo", "Obedience", "Obœdientia", "Luke 2:22-38"),
        ("The Finding in the Temple", "Inventio in Templo", "Piety", "Pietas", "Luke 2:41-52"),
    ]),
    "sorrowful": ("The Sorrowful Mysteries", "Mysteria Dolorosa", [
        ("The Agony in the Garden", "Agonia in Horto", "Sorrow for sin", "Contritio peccatorum",
         "Matthew 26:36-46"),
        ("The Scourging at the Pillar", "Flagellatio", "Mortification", "Mortificatio", "John 19:1"),
        ("The Crowning with Thorns", "Coronatio Spinis", "Moral courage", "Fortitudo", "Matthew 27:27-31"),
        ("The Carrying of the Cross", "Baiulatio Crucis", "Patience", "Patientia", "John 19:16-17"),
        ("The Crucifixion", "Crucifixio et Mors Domini", "Final perseverance", "Perseverantia finalis",
         "Luke 23:33-46"),
    ]),
    "glorious": ("The Glorious Mysteries", "Mysteria Gloriosa", [
        ("The Resurrection", "Resurrectio Domini", "Faith", "Fides", "Matthew 28:1-10"),
        ("The Ascension", "Ascensio Domini", "Hope and desire for Heaven", "Spes et desiderium cæli",
         "Acts 1:6-11"),
        ("The Descent of the Holy Ghost", "Descensus Spiritus Sancti", "Love of God", "Amor Dei", "Acts 2:1-4"),
        ("The Assumption of Our Lady", "Assumptio B. M. V.", "Grace of a happy death", "Gratia bonæ mortis",
         "Apocalypse 12:1"),
        ("The Coronation of Our Lady", "Coronatio B. M. V.", "Trust in Mary's intercession",
         "Fiducia in Mariam", "Apocalypse 12:1-5"),
    ]),
}


def mysteries_for(day=None):
    """Traditional weekday scheme; on Sundays the set follows the season."""
    day = day or dt.date.today()
    wd = day.weekday()                       # Monday = 0
    if wd in (0, 3):
        return "joyful"
    if wd in (1, 4):
        return "sorrowful"
    if wd in (2, 5):
        return "glorious"
    season = liturgy.day_info(day).season
    if season in ("advent", "christmas", "epiphany", "septuagesima"):
        return "joyful"
    if season in ("lent", "passiontide"):
        return "sorrowful"
    return "glorious"


def rosary_steps(key):
    """A flat list of steps: (bead kind, prayer key, heading EN, heading LA, note EN, note LA)."""
    steps = [("cross", "signum", "", "", "", ""), ("cross", "credo", "", "", "", ""),
             ("large", "pater", "", "", "", "")]
    for i, (en, la) in enumerate((("For an increase of faith", "Pro augmento fidei"),
                                  ("For an increase of hope", "Pro augmento spei"),
                                  ("For an increase of charity", "Pro augmento caritatis"))):
        steps.append(("small", "ave", "", "", en, la))
    steps.append(("none", "gloria", "", "", "", ""))
    ordinals = (("First", "Primum"), ("Second", "Secundum"), ("Third", "Tertium"), ("Fourth", "Quartum"),
                ("Fifth", "Quintum"))
    for n, (en, la, f_en, f_la, ref) in enumerate(MYSTERIES[key][2]):
        head_en = f"{ordinals[n][0]} Mystery: {en}"
        head_la = f"Mysterium {ordinals[n][1]}: {la}"
        note_en, note_la = f"Fruit of the mystery: {f_en} · {ref}", f"Fructus mysterii: {f_la}"
        steps.append(("large", "pater", head_en, head_la, note_en, note_la))
        for k in range(10):
            steps.append(("small", "ave", head_en, head_la, f"{k + 1} / 10", f"{k + 1} / 10"))
        steps.append(("none", "gloria", head_en, head_la, "", ""))
        steps.append(("none", "fatima", head_en, head_la, "", ""))
    steps.append(("none", "salve", "", "", "", ""))
    steps.append(("none", "rosary_oratio", "", "", "", ""))
    steps.append(("cross", "signum", "", "", "", ""))
    return steps


def marian_antiphon_key(day=None):
    """Angelus most of the year; Regina Caeli from Easter until the Saturday after Pentecost."""
    day = day or dt.date.today()
    off = (day - liturgy.easter(day.year)).days
    return "regina" if 0 <= off <= 55 else "angelus"


# ------------------------------------------------------------------ Examination of conscience
EXAMEN = [
    ("I. I am the Lord thy God; thou shalt not have strange gods before Me.",
     "Ego sum Dominus Deus tuus: non habebis deos alienos coram me.",
     ["Have I neglected my daily prayers, or prayed without attention?",
      "Have I doubted or denied a truth of the Faith, or put my faith in danger by reading or company?",
      "Have I been involved in superstition, fortune-telling, occultism or false religions?",
      "Have I despaired of God's mercy, or presumed on it to keep sinning?",
      "Have I received Holy Communion in a state of mortal sin, or hidden a mortal sin in Confession?"]),
    ("II. Thou shalt not take the name of the Lord thy God in vain.",
     "Non assumes nomen Domini Dei tui in vanum.",
     ["Have I used the holy name of God or of Jesus carelessly, in anger or in jest?",
      "Have I cursed, blasphemed, or spoken irreverently of holy things?",
      "Have I sworn falsely or without need, or broken a vow?"]),
    ("III. Remember thou keep holy the Sabbath day.",
     "Memento ut diem sabbati sanctifices.",
     ["Have I missed Mass on a Sunday or holy day of obligation through my own fault?",
      "Have I come late or left early without reason, or been irreverent in church?",
      "Have I done unnecessary servile work on Sunday?"]),
    ("IV. Honour thy father and thy mother.",
     "Honora patrem tuum et matrem tuam.",
     ["Have I been disobedient or disrespectful to my parents or lawful superiors?",
      "Have I neglected my duties to my spouse, children or family?",
      "Have I failed to give my children a Catholic education and good example?"]),
    ("V. Thou shalt not kill.",
     "Non occides.",
     ["Have I harbored hatred, anger or desire for revenge, or refused to forgive?",
      "Have I injured anyone, or harmed my own health by excess in food, drink or drugs?",
      "Have I given scandal, leading others into sin?",
      "Have I taken part in or approved of abortion, euthanasia or suicide?"]),
    ("VI. Thou shalt not commit adultery.",
     "Non mœchaberis.",
     ["Have I been unchaste in thought, word or deed, alone or with others?",
      "Have I looked at impure images or entertainment?",
      "Have I failed in the duties or the purity of married life?"]),
    ("VII. Thou shalt not steal.",
     "Non furtum facies.",
     ["Have I stolen, cheated, or kept what belongs to another?",
      "Have I damaged another's property, or failed to make restitution?",
      "Have I been lazy in my work, or wasteful, or failed to help the poor?"]),
    ("VIII. Thou shalt not bear false witness against thy neighbour.",
     "Non loqueris contra proximum tuum falsum testimonium.",
     ["Have I lied?", "Have I harmed another's reputation by calumny or by revealing faults without need?",
      "Have I judged others rashly, or revealed secrets entrusted to me?"]),
    ("IX. Thou shalt not covet thy neighbour's wife.",
     "Non desiderabis uxorem proximi tui.",
     ["Have I willfully entertained impure desires or thoughts?"]),
    ("X. Thou shalt not covet thy neighbour's goods.",
     "Non concupisces rem proximi tui.",
     ["Have I been envious of others' possessions or success?",
      "Have I been greedy, or placed my heart on money and things?"]),
    ("The Precepts of the Church", "Præcepta Ecclesiæ",
     ["Have I kept the days of fasting and abstinence (including Friday abstinence)?",
      "Have I confessed at least once a year, and received Holy Communion during Eastertide?",
      "Have I contributed to the support of the Church?",
      "Have I observed the laws of the Church concerning marriage?"]),
    ("The Seven Capital Sins", "Septem peccata capitalia",
     ["Pride (superbia): vanity, ambition, contempt of others?", "Avarice (avaritia)?",
      "Lust (luxuria)?", "Anger (ira)?", "Gluttony (gula)?", "Envy (invidia)?",
      "Sloth (acedia): neglect of spiritual duties?"]),
]

CONFESSION_GUIDE = (
    "Go to the priest and make the Sign of the Cross. Say: \"Bless me, Father, for I have sinned. It has been "
    "[time] since my last confession.\" Confess your sins, mortal sins by kind and number. End with: \"For "
    "these and all the sins of my past life, I am sorry.\" Listen to the priest's counsel and penance, then "
    "make an Act of Contrition while he gives absolution. Perform your penance promptly.")
