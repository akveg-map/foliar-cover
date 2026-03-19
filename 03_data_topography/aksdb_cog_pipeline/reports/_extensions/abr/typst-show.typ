#let abr-report(
  title: none,
  project-footer: none,
  author: none,
  email: none,
  date-str: none,
  client: (),
  body
) = {
  // Global document settings
  set page(
    paper: "us-letter",
    margin: (top: 1in, bottom: 1in, left: 1in, right: 1in),
    footer: context {
      if counter(page).get().first() > 1 {
        let page-number = counter(page).display()
        let total-pages = counter(page).final().first()
        
        set text(font: "Poppins", size: 8pt, fill: gray.darken(20%))
        line(length: 100%, stroke: 0.5pt + gray)
        v(4pt)
        grid(
          columns: (auto, auto, 1fr, auto),
          column-gutter: 1.5em,
          align: horizon,
          image("_extensions/abr/logos/akveg_logo.png", height: 0.2in),
          image("_extensions/abr/logos/ABR_logo-color.svg", height: 0.2in),
          [#project-footer],
          [Page #page-number of #total-pages]
        )
      }
    }
  )

  set text(font: "TeX Gyre Termes", size: 11pt)

  // Heading styles
  show heading: it => {
    let size = 12pt
    if it.level == 1 { size = 16pt }
    else if it.level == 2 { size = 14pt }
    
    block(above: 1.5em, below: 1em)[
      #set text(font: "Mada", fill: rgb("286464"), weight: "bold", size: size)
      #it
    ]
  }

  // Title Page
  if title != none {
    set page(margin: (top: 1in, bottom: 1in, left: 1in, right: 1in))
    block(width: 100%, height: 100%)[
      #set text(font: "Poppins")
      #v(1.5in)
      #align(center)[
        #text(size: 26pt, weight: "bold", fill: rgb("286464"))[#title]
        #v(2em)
        #line(length: 30%, stroke: 1.5pt + rgb("286464"))
        #v(3em)
      ]
      
      #grid(
        columns: (1fr, 1fr),
        column-gutter: 10%,
        [
          #set align(left)
          #set text(size: 10pt)
          #upper(text(weight: "bold", fill: gray)[Prepared for]) \
          #v(0.5em)
          #text(size: 11pt)[
            #client.name \
            #client.addr-1 \
            #client.addr-2 \
            #client.addr-3 \
            #client.addr-4
          ]
          #v(2.5em)
          #upper(text(weight: "bold", fill: gray)[Prepared by]) \
          #v(0.5em)
          #text(size: 11pt)[
            #author \
            #email
          ]
        ],
        [
          #set align(center)
          #v(1em)
          #grid(
            columns: (1fr, 1fr),
            column-gutter: 1.5em,
            align: horizon,
            image("_extensions/abr/logos/akveg_logo.png", width: 100%),
            image("_extensions/abr/logos/ABR_full_logo-color.svg", width: 100%)
          )
          #v(4em)
          #text(size: 12pt, weight: "medium")[#date-str] \
          #v(0.5em)
          #link("https://akveg.org")[akveg.org]
        ]
      )
    ]
    pagebreak()
  }

  body
}

#show: doc => abr-report(
  title: $if(project-title)$[$project-title$]$else$none$endif$,
  project-footer: $if(project-footer)$[$project-footer$]$else$none$endif$,
  author: $if(author)$[$author$]$else$none$endif$,
  email: $if(email)$[$email$]$else$none$endif$,
  date-str: $if(date-str)$[$date-str$]$else$none$endif$,
  client: (
    name: $if(client.name)$[$client.name$]$else$none$endif$,
    addr-1: $if(client.addr-1)$[$client.addr-1$]$else$none$endif$,
    addr-2: $if(client.addr-2)$[$client.addr-2$]$else$none$endif$,
    addr-3: $if(client.addr-3)$[$client.addr-3$]$else$none$endif$,
    addr-4: $if(client.addr-4)$[$client.addr-4$]$else$none$endif$
  ),
  doc
)
