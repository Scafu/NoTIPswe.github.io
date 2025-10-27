#import "base_document.typ" as base-document

#let INTERNAL_SCOPE = base-document.INTERNAL_SCOPE
#let EXTERNAL_SCOPE = base-document.EXTERNAL_SCOPE

#let apply-base-verbale(
  date: "",
  scope: "",
  front-info: (),
  abstract: "",
  changelog: (),
  odg,
  discussion,
  other,
) = {
  base-document.apply-base-document(
    title: "Verbale " + scope + " del " + date,
    abstract: abstract,
    changelog: changelog,
    scope: scope,
    front-info: front-info,
  )[

    = Info e Ordine del Giorno
    #odg

    = Discussione
    #discussion

    #other
  ]
}
