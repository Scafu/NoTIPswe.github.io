#import "../templates/conf.typ": conf

#let changelog = yaml(sys.inputs.changelog_path)

#show: conf.with(
  title: sys.inputs.doc_title,
  changelog_content: changelog,
)

= Prova BBB

#lorem(200)

= Prova AAA

#lorem(300)

== Prova aaa

#lorem(100)

=== Prova aa

==== Prova aaaaaa

====== sos

