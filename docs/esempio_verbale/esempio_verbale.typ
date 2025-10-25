#import "../templates/base_report.typ" as base-verbale

#let changelog = yaml(sys.inputs.changelog_path)

#base-verbale.apply-base-verbale(
  date: "2025-10-25",
  scope: base-verbale.INTERNAL_SCOPE,
  changelog: changelog,
)[
  #lorem(400)
][
  #lorem(300)
][

  = Prova BBB

  #lorem(200)

  = Prova AAA

  #lorem(300)

  == Prova aaa

  #lorem(100)

  === Prova aa

  ==== Prova aaaaaa

]
