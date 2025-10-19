 #let front_matter(title, version) = {
  set align(center + horizon)
  set page(header: none, footer: none)

  text(size: 24pt, weight: "bold")[#title]
  linebreak()
  text(size: 16pt)[Versione #version]

  pagebreak()
}


#let changelog(changelog_content) = {
  heading(level: 1, outlined: false, numbering: none)[Changelog]

  let formatNamesForChangelog(names) = {
    names.map(n => n.split(" ").join("\n")).sorted().join(",\n")
  }

  table(
    columns: (auto, auto, auto, auto, 1fr),
    align: (center, left, left, left, left),

    table.header[Versione][Data][Autori][Verificatori][Descrizione],

    ..changelog_content.map(c => (
      str(c.version),
      c.date,
      formatNamesForChangelog(c.authors),
      formatNamesForChangelog(c.verifiers),
      c.description
    )).flatten()
  )

  pagebreak()
}


#let toc() = {
  outline()

  pagebreak()
}

#let figure_list() = context {
  let figs = query(figure.where(kind: image))

  if figs.len() > 0 {
    outline(title: "Indice delle figure", target: figure.where(kind: image))

    pagebreak()
  }
}

#let conf(
  title: "Titolo di Default",
  changelog_content: (),
  doc
) = {
  set text(lang: "it", size: 12pt)
  set page(
    paper: "a4",
    numbering: "1 / 1"
  )
  set align(top + left)
  set heading(numbering: "1.1")
  show table.cell.where(y: 0): strong

  changelog_content = changelog_content.sorted(key: c => c.version).rev()

  front_matter(title, changelog_content.map(c => c.version).sorted().last())

  counter(page).update(1)

  changelog(changelog_content)
  toc()
  figure_list()

  doc
}

