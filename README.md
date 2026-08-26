# img-to-vector

Zet logo's (png, jpg, webp, gif, bmp, tiff) om naar vectoren met potrace. De vector is altijd zwart en heeft altijd een transparante achtergrond.

## Starten

```
./run.sh
```

Zet je bestanden in `input/`, draai het commando, en `output/` vult zich met een `.svg`, `.pdf` en `.eps` per bestand. De eerste keer zet `run.sh` zelf de pipenv-omgeving op, daarna start hij meteen.

Staat de omgeving er eenmaal, dan kan het ook direct:

```
pipenv run vectorize
pipenv run test
```

Vlaggen mag je achter allebei zetten: `./run.sh --formats svg` of `pipenv run vectorize --threshold 0.6`.

## Wat wordt er zwart

De tool zoekt zelf uit wat de vorm van je logo is:

- Heeft het bestand een alfakanaal met echte transparantie, dan is "ondoorzichtig" de vorm. De kleur van het logo maakt dan niet uit, wit op transparant werkt net zo goed als zwart op transparant.
- Anders bepaalt de helderheid het, en kijkt hij naar de vier hoeken om te zien of de achtergrond licht of donker is. Een wit logo op een zwarte achtergrond komt er dus ook goed uit.

Klopt het toch niet, dan zijn `--invert` en `--threshold` de knoppen om aan te draaien.

## Opties

| Vlag | Standaard | Waarvoor |
| --- | --- | --- |
| `--input` | `input` | map met afbeeldingen |
| `--output` | `output` | map voor de vectoren |
| `--formats` | `svg,pdf,eps` | welke bestanden je terugkrijgt |
| `--threshold` | `0.5` | grens tussen vorm en achtergrond |
| `--invert` | uit | draai vorm en achtergrond om |
| `--turdsize` | `2` | onderdruk vlekjes tot deze grootte |
| `--alphamax` | `1.0` | lager is hoekiger, hoger is ronder |
| `--min-size` | `0` | vergroot een klein logo eerst tot deze grootte |

`--min-size` staat bewust uit. Opschalen maakt de curves niet gladder maar juist grilliger, omdat potrace de rimpel van de interpolatie meetraceert. Bij een logo van een paar honderd pixels kost het vijftien keer zoveel bytes voor niets. Alleen bij een echt klein icoontje (rond de 64 pixels) levert `--min-size 1000` meetbaar een betere vorm op.

## Hoe het werkt

Potrace leest zelf geen png of jpg, alleen zwart-wit bitmaps, dus er zit altijd een voorbewerking tussen. De stappen staan elk in hun eigen module:

- `img2vec/preprocess.py` maakt van de afbeelding een grijswaardenmasker waarin de vorm donker is
- `img2vec/trace.py` laat potrace daar contouren van maken, op de oorspronkelijke schaal
- `img2vec/backends.py` schrijft die contouren weg als svg, eps en pdf
- `img2vec/cli.py` loopt door de map en houdt de voortgang bij

Het tracen gebeurt met [potracer](https://pypi.org/project/potracer/), een pure-Python port van potrace. Er is dus niets systeembreed nodig, alles zit in de pipenv-omgeving van de repo.
