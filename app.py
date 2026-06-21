from flask import Flask, render_template, request

import digest
import storage
from sources import load_profile

app = Flask(__name__)


@app.route("/")
def index():
    conn = storage.connect()
    promotions = storage.get_all_promotions(conn)
    profile = load_profile()

    typy = sorted({p.typ for p in promotions})
    partnerzy = sorted({p.partner for p in promotions if p.partner})
    regiony = sorted({r for p in promotions for r in p.regiony})

    wybrany_typ = request.args.get("typ", "")
    wybrany_partner = request.args.get("partner", "")
    wybrany_region = request.args.get("region", "")

    if wybrany_typ:
        promotions = [p for p in promotions if p.typ == wybrany_typ]
    if wybrany_partner:
        promotions = [p for p in promotions if p.partner == wybrany_partner]
    if wybrany_region:
        promotions = [p for p in promotions if wybrany_region in p.regiony]

    return render_template(
        "index.html",
        promotions=promotions,
        is_relevant=lambda p: digest.is_relevant(p, profile),
        typy=typy,
        partnerzy=partnerzy,
        regiony=regiony,
        wybrany_typ=wybrany_typ,
        wybrany_partner=wybrany_partner,
        wybrany_region=wybrany_region,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
