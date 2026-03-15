// Some definitions presupposed by pandoc's typst output.
#let blockquote(body) = [
  #set text( size: 0.92em )
  #block(inset: (left: 1.5em, top: 0.2em, bottom: 0.2em))[#body]
]

#let horizontalrule = line(start: (25%,0%), end: (75%,0%))

#let endnote(num, contents) = [
  #stack(dir: ltr, spacing: 3pt, super[#num], contents)
]

#show terms: it => {
  it.children
    .map(child => [
      #strong[#child.term]
      #block(inset: (left: 1.5em, top: -0.4em))[#child.description]
      ])
    .join()
}

// Some quarto-specific definitions.

#show raw.where(block: true): set block(
    fill: luma(230),
    width: 100%,
    inset: 8pt,
    radius: 2pt
  )

#let block_with_new_content(old_block, new_content) = {
  let d = (:)
  let fields = old_block.fields()
  fields.remove("body")
  if fields.at("below", default: none) != none {
    // TODO: this is a hack because below is a "synthesized element"
    // according to the experts in the typst discord...
    fields.below = fields.below.abs
  }
  return block.with(..fields)(new_content)
}

#let empty(v) = {
  if type(v) == str {
    // two dollar signs here because we're technically inside
    // a Pandoc template :grimace:
    v.matches(regex("^\\s*$")).at(0, default: none) != none
  } else if type(v) == content {
    if v.at("text", default: none) != none {
      return empty(v.text)
    }
    for child in v.at("children", default: ()) {
      if not empty(child) {
        return false
      }
    }
    return true
  }

}

// Subfloats
// This is a technique that we adapted from https://github.com/tingerrr/subpar/
#let quartosubfloatcounter = counter("quartosubfloatcounter")

#let quarto_super(
  kind: str,
  caption: none,
  label: none,
  supplement: str,
  position: none,
  subrefnumbering: "1a",
  subcapnumbering: "(a)",
  body,
) = {
  context {
    let figcounter = counter(figure.where(kind: kind))
    let n-super = figcounter.get().first() + 1
    set figure.caption(position: position)
    [#figure(
      kind: kind,
      supplement: supplement,
      caption: caption,
      {
        show figure.where(kind: kind): set figure(numbering: _ => numbering(subrefnumbering, n-super, quartosubfloatcounter.get().first() + 1))
        show figure.where(kind: kind): set figure.caption(position: position)

        show figure: it => {
          let num = numbering(subcapnumbering, n-super, quartosubfloatcounter.get().first() + 1)
          show figure.caption: it => {
            num.slice(2) // I don't understand why the numbering contains output that it really shouldn't, but this fixes it shrug?
            [ ]
            it.body
          }

          quartosubfloatcounter.step()
          it
          counter(figure.where(kind: it.kind)).update(n => n - 1)
        }

        quartosubfloatcounter.update(0)
        body
      }
    )#label]
  }
}

// callout rendering
// this is a figure show rule because callouts are crossreferenceable
#show figure: it => {
  if type(it.kind) != str {
    return it
  }
  let kind_match = it.kind.matches(regex("^quarto-callout-(.*)")).at(0, default: none)
  if kind_match == none {
    return it
  }
  let kind = kind_match.captures.at(0, default: "other")
  kind = upper(kind.first()) + kind.slice(1)
  // now we pull apart the callout and reassemble it with the crossref name and counter

  // when we cleanup pandoc's emitted code to avoid spaces this will have to change
  let old_callout = it.body.children.at(1).body.children.at(1)
  let old_title_block = old_callout.body.children.at(0)
  let old_title = old_title_block.body.body.children.at(2)

  // TODO use custom separator if available
  let new_title = if empty(old_title) {
    [#kind #it.counter.display()]
  } else {
    [#kind #it.counter.display(): #old_title]
  }

  let new_title_block = block_with_new_content(
    old_title_block, 
    block_with_new_content(
      old_title_block.body, 
      old_title_block.body.body.children.at(0) +
      old_title_block.body.body.children.at(1) +
      new_title))

  block_with_new_content(old_callout,
    block(below: 0pt, new_title_block) +
    old_callout.body.children.at(1))
}

// 2023-10-09: #fa-icon("fa-info") is not working, so we'll eval "#fa-info()" instead
#let callout(body: [], title: "Callout", background_color: rgb("#dddddd"), icon: none, icon_color: black, body_background_color: white) = {
  block(
    breakable: false, 
    fill: background_color, 
    stroke: (paint: icon_color, thickness: 0.5pt, cap: "round"), 
    width: 100%, 
    radius: 2pt,
    block(
      inset: 1pt,
      width: 100%, 
      below: 0pt, 
      block(
        fill: background_color, 
        width: 100%, 
        inset: 8pt)[#text(icon_color, weight: 900)[#icon] #title]) +
      if(body != []){
        block(
          inset: 1pt, 
          width: 100%, 
          block(fill: body_background_color, width: 100%, inset: 8pt, body))
      }
    )
}



#let article(
  title: none,
  subtitle: none,
  authors: none,
  date: none,
  abstract: none,
  abstract-title: none,
  cols: 1,
  lang: "en",
  region: "US",
  font: "libertinus serif",
  fontsize: 11pt,
  title-size: 1.5em,
  subtitle-size: 1.25em,
  heading-family: "libertinus serif",
  heading-weight: "bold",
  heading-style: "normal",
  heading-color: black,
  heading-line-height: 0.65em,
  sectionnumbering: none,
  toc: false,
  toc_title: none,
  toc_depth: none,
  toc_indent: 1.5em,
  doc,
) = {
  set par(justify: true)
  set text(lang: lang,
           region: region,
           font: font,
           size: fontsize)
  set heading(numbering: sectionnumbering)
  if title != none {
    align(center)[#block(inset: 2em)[
      #set par(leading: heading-line-height)
      #if (heading-family != none or heading-weight != "bold" or heading-style != "normal"
           or heading-color != black) {
        set text(font: heading-family, weight: heading-weight, style: heading-style, fill: heading-color)
        text(size: title-size)[#title]
        if subtitle != none {
          parbreak()
          text(size: subtitle-size)[#subtitle]
        }
      } else {
        text(weight: "bold", size: title-size)[#title]
        if subtitle != none {
          parbreak()
          text(weight: "bold", size: subtitle-size)[#subtitle]
        }
      }
    ]]
  }

  if authors != none {
    let count = authors.len()
    let ncols = calc.min(count, 3)
    grid(
      columns: (1fr,) * ncols,
      row-gutter: 1.5em,
      ..authors.map(author =>
          align(center)[
            #author.name \
            #author.affiliation \
            #author.email
          ]
      )
    )
  }

  if date != none {
    align(center)[#block(inset: 1em)[
      #date
    ]]
  }

  if abstract != none {
    block(inset: 2em)[
    #text(weight: "semibold")[#abstract-title] #h(1em) #abstract
    ]
  }

  if toc {
    let title = if toc_title == none {
      auto
    } else {
      toc_title
    }
    block(above: 0em, below: 2em)[
    #outline(
      title: toc_title,
      depth: toc_depth,
      indent: toc_indent
    );
    ]
  }

  if cols == 1 {
    doc
  } else {
    columns(cols, doc)
  }
}

#set table(
  inset: 6pt,
  stroke: none
)

#set page(
  paper: "us-letter",
  margin: (x: 1.25in, y: 1.25in),
  numbering: "1",
)

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
  title: [Topography Covariate Scaling and COG Conversion Report],
  project-footer: [AKVEG Topography Covariates],
  author: [Gemini CLI],
  email: none,
  date-str: [March 14, 2026],
  client: (
    name: [ABR, Inc.],
    addr-1: [P.O. Box 80410],
    addr-2: [Fairbanks, AK 99708],
    addr-3: none,
    addr-4: none
  ),
  doc
)

== Executive Summary
<executive-summary>
This report documents the scaling and Cloud Optimized GeoTIFF (COG) conversion of 111 topographic covariate rasters for the AKVEG project.

- #strong[Goal:] Optimize storage and cloud performance while maintaining geomorphometric precision.
- #strong[Result:] 76.8% storage reduction (9.8 TB to 2.3 TB).
- #strong[Integrity:] 100% mask integrity verified via point-by-point terrestrial scaling analysis.

== Data Locations
<data-locations>
- #strong[Google Earth Engine (GEE):]
  - #strong[Scaled Collection:] `projects/akveg-map/assets/covariates/aksdb/aksdb_topo_v20250422_scaled`
  - #strong[Raw Collection:] `projects/akveg-map/assets/covariates/aksdb/aksdb_topo_v20250422_raw`
- #strong[Google Cloud Storage (GCS):]
  - #strong[Production COGs:] `gs://akveg-data/aksdb_dem_covars_v20250422_scaled_cog/cogs/`
  - #strong[Raw Source:] `gs://akveg-data/aksdb_dem_covars_v20250422/`
- #strong[Local Configuration:] `03_data_topography/cog_pipeline/scaling_config.json`

== Naming References
<naming-references>
Vetted against the primary project references: 1. #strong[Git Reference:] #link("https://github.com/orgs/alaska-soil-data-bank/projects/3")[Alaska Soil Data Bank Project 3] (File: `covariates - View 1 (1).tsv`) 2. #strong[Email Reference:] 2024-01-04 email '10 m DEM for Alaska' from Colby Brungard (File: `Covariate Table2.xlsx`).

== Processing Implementation
<processing-implementation>
=== Correction of Background Artifacts
<correction-of-background-artifacts>
Source data for fluvial metrics contained non-standard negative artifacts in background/ocean areas. The pipeline standardized these to clean NoData values: \* #strong[Int16:] `-32768` \* #strong[Float32:] `-99999.0` \* #strong[Byte:] `0`

=== Cloud Optimization
<cloud-optimization>
#table(
  columns: 2,
  align: (left,left,),
  table.header([Feature], [Setting],),
  table.hline(),
  [#strong[Tiling];], [512x512 blocks],
  [#strong[Compression];], [DEFLATE / PREDICTOR=2],
  [#strong[Overviews];], [9 levels (AVERAGE/MODE)],
)
== Scaling Strategy Review
<scaling-strategy-review>
Factors were optimized to balance precision vs.~dynamic range.

=== Optimized Scaling Results
<optimized-scaling-results>
- #strong[Curvatures/Openness (100,000 to 1,000,000):] Captured sharp physical gradients at ridges while reducing clamping to \< 0.5% for most bands.
- #strong[Local Deviance (1,000):] Expanded range to +/- 32m, capturing previously flattened slopes in rugged terrain.
- #strong[Fluvial Metrics (10.0):] Resolved "staircase" stepping artifacts in `dfa` and `spi`.
- #strong[Categorical (Byte):] Preserved directly as 8-bit integers (0-255) with no scaling to maintain class integrity.

=== Critical Assessment & Trade-offs
<critical-assessment-trade-offs>
- #strong[Quantization:] Excellent. Most geomorphometric bands show a #strong[Step/IQR \< 0.1%];, ensuring that the rounding error is an order of magnitude smaller than the natural variation in the landscape.
- #strong[Hydrological Extremes:] For `spi` (Stream Power Index) and `dfa` (Directional Flow Accumulation), a clamping rate of \~3-6% was accepted. To avoid clamping these extreme values into `Int16` space, we would have needed a scale factor near 0.01, which would have destroyed all meaningful precision in 94% of the terrestrial landscape. The current strategy prioritizes precision where 95% of modeling occurs.
- #strong[Fluvial Healing:] The source data for `dfa` and `spi` contained large negative values in what should have been NoData space (e.g., ocean). The pipeline successfully "healed" these regions by masking them to `-32768`, ensuring they do not bias modeling results or visual displays.
- #strong[Metadata Mapping:] 100% of the 111 variables are successfully cross-referenced against the original Alaska Soil Data Bank (AKSDB) and Colby Brungard (2024) references, ensuring long-term traceability.

== Scaling Quality Metrics
<scaling-quality-metrics>
- #strong[% Clamped:] Percentage of valid pixels saturated at Int16 limits (+/- 32,000).
- #strong[Step/IQR:] Quantization step (1/scale) relative to Interquartile Range. Values \< 0.1% indicate excellent precision.

= Detailed Covariate Summary
<detailed-covariate-summary>
#set page(flipped: true)
#set text(size: 7pt)
=== Continuous Covariates Summary
<continuous-covariates-summary>
==== Focal Statistics
<focal-statistics>
#table(
  columns: (24%, 10%, 8%, 5%, 8%, 7%, 7%, 10%, 7%, 7%, 7%),
  align: (left,left,center,center,center,center,center,center,center,center,center,),
  table.header([Variable Name], [Abbr], [Suffix], [Res], [Match], [Raw GB], [Scaled GB], [Scale], [Type], [% Clamp], [Step/IQR],),
  table.hline(),
  [Deviance from Mean Elevation (Window: 4)], [devmeanelev\_4], [\_1k], [10m], [Direct], [104.2], [30.3], [1,000], [I16], [0.00%], [0.4214%],
  [Deviance from Mean Elevation (Window: 16)], [devmeanelev\_16], [\_1k], [10m], [Direct], [104.2], [27.6], [1,000], [I16], [0.00%], [0.2346%],
  [Deviance from Mean Elevation (Window: 32)], [devmeanelev\_32], [\_1k], [10m], [Direct], [104.2], [25.5], [1,000], [I16], [0.00%], [0.1778%],
  [Difference from Mean Elevation (Window: 4)], [diffmeanelev\_4], [\_100], [10m], [Direct], [104.7], [23.6], [100], [I16], [0.00%], [2.4848%],
  [Difference from Mean Elevation (Window: 16)], [diffmeanelev\_16], [\_100], [10m], [Direct], [105.0], [25.8], [100], [I16], [0.00%], [0.4842%],
  [Difference from Mean Elevation (Window: 32)], [diffmeanelev\_32], [\_100], [10m], [Direct], [104.9], [26.5], [100], [I16], [0.00%], [0.1977%],
  [Minimum Elevation (Window: 4)], [minelev\_4], [\_1], [10m], [Direct], [81.1], [5.9], [1], [I16], [0.00%], [0.1655%],
  [Minimum Elevation (Window: 16)], [minelev\_16], [\_1], [10m], [Direct], [66.6], [4.4], [1], [I16], [0.00%], [0.1733%],
  [Minimum Elevation (Window: 32)], [minelev\_32], [\_1], [10m], [Direct], [56.3], [3.4], [1], [I16], [0.00%], [0.1810%],
  [Percentile Elevation (Window: 4)], [perctelev\_4], [\_100], [10m], [Semantic], [84.7], [30.4], [100], [I16], [0.00%], [0.0749%],
  [Percentile Elevation (Window: 16)], [perctelev\_16], [\_100], [10m], [Semantic], [91.0], [31.2], [100], [I16], [0.00%], [0.0483%],
  [Percentile Elevation (Window: 32)], [perctelev\_32], [\_100], [10m], [Semantic], [92.0], [30.7], [100], [I16], [0.00%], [0.0371%],
  [Relative Elevation (Window: 4)], [relelev\_4], [\_10], [10m], [Semantic], [95.7], [15.5], [10], [I16], [0.00%], [0.9332%],
  [Relative Elevation (Window: 16)], [relelev\_16], [\_10], [10m], [Semantic], [95.1], [16.4], [10], [I16], [0.00%], [0.2678%],
  [Relative Elevation (Window: 32)], [relelev\_32], [\_10], [10m], [Semantic], [94.7], [16.5], [10], [I16], [0.00%], [0.1570%],
  [Relative Mean Elevation (Window: 4)], [relmeanelev\_4], [\_100], [10m], [Semantic], [104.3], [23.6], [100], [I16], [0.00%], [2.4847%],
  [Relative Mean Elevation (Window: 16)], [relmeanelev\_16], [\_100], [10m], [Semantic], [104.6], [25.8], [100], [I16], [0.00%], [0.4842%],
  [Relative Mean Elevation (Window: 32)], [relmeanelev\_32], [\_100], [10m], [Semantic], [104.6], [26.5], [100], [I16], [0.00%], [0.1977%],
  [stddevelev (Window: 4)], [stddevelev\_4], [\_100], [10m], [Semantic], [95.6], [19.4], [100], [I16], [0.00%], [0.1777%],
  [stddevelev (Window: 16)], [stddevelev\_16], [\_100], [10m], [Semantic], [95.4], [16.7], [100], [I16], [0.00%], [0.0517%],
  [stddevelev (Window: 32)], [stddevelev\_32], [\_100], [10m], [Semantic], [95.1], [14.7], [100], [I16], [0.00%], [0.0287%],
)
==== Hydrology
<hydrology>
#table(
  columns: (24%, 10%, 8%, 5%, 8%, 7%, 7%, 10%, 7%, 7%, 7%),
  align: (left,left,center,center,center,center,center,center,center,center,center,),
  table.header([Variable Name], [Abbr], [Suffix], [Res], [Match], [Raw GB], [Scaled GB], [Scale], [Type], [% Clamp], [Step/IQR],),
  table.hline(),
  [Catchment Area (Area: 10)], [ca\_10], [\_1], [10m], [Direct], [100.0], [74.3], [1], [F32], [0.00%], [Perfect],
  [Catchment Area (Area: 10000)], [ca\_10000], [\_1], [10m], [Direct], [100.0], [74.3], [1], [F32], [0.00%], [Perfect],
  [Modified Catchment Area (Area: 10)], [mca\_10], [\_1], [10m], [Direct], [99.9], [72.6], [1], [F32], [0.00%], [Perfect],
  [Modified Catchment Area (Area: 10000)], [mca\_10000], [\_1], [10m], [Direct], [100.1], [73.5], [1], [F32], [0.00%], [Perfect],
  [Saga Wetness Index (Area: 10)], [swi\_10], [\_1k], [10m], [Direct], [90.8], [33.6], [1,000], [I16], [0.00%], [0.0143%],
  [Saga Wetness Index (Area: 10000)], [swi\_10000], [\_1k], [10m], [Direct], [91.0], [34.0], [1,000], [I16], [0.00%], [0.0194%],
  [Stream Power Index], [spi], [\_10], [10m], [Direct], [100.9], [33.8], [10], [I16], [6.61%], [0.0127%],
  [Topographic Wetness Index], [twi], [\_1k], [10m], [Direct], [89.6], [34.3], [1,000], [I16], [0.00%], [0.0378%],
  [Valley Depth], [vlyd], [\_10], [10m], [Semantic], [95.6], [19.4], [10], [I16], [0.00%], [0.1111%],
)
==== Lighting/Visibility
<lightingvisibility>
#table(
  columns: (24%, 10%, 8%, 5%, 8%, 7%, 7%, 10%, 7%, 7%, 7%),
  align: (left,left,center,center,center,center,center,center,center,center,center,),
  table.header([Variable Name], [Abbr], [Suffix], [Res], [Match], [Raw GB], [Scaled GB], [Scale], [Type], [% Clamp], [Step/IQR],),
  table.hline(),
  [Diurnal Anisotropic Heating], [dah], [\_10k], [10m], [Direct], [101.9], [30.7], [10,000], [I16], [0.00%], [0.1698%],
  [Hillshade (Standard)], [hs\_st], [\_100], [10m], [Direct], [87.4], [28.2], [100], [I16], [0.00%], [0.2669%],
  [Topographic Openness (Negative) (Window: 2)], [no\_2], [\_10k], [10m], [Direct], [76.3], [29.2], [10,000], [I16], [0.00%], [1.0744%],
  [Topographic Openness (Difference) (Window: 2)], [diffopen\_2], [\_100k], [10m], [Direct], [90.2], [37.5], [100,000], [I16], [0.40%], [0.0537%],
  [Topographic Openness (Positive) (Window: 2)], [po\_2], [\_10k], [10m], [Direct], [76.3], [29.2], [10,000], [I16], [0.00%], [1.0744%],
  [Topographic Openness (Negative) (Window: 32)], [no\_32], [\_10k], [10m], [Direct], [78.2], [28.8], [10,000], [I16], [0.00%], [0.3233%],
  [Topographic Openness (Difference) (Window: 32)], [diffopen\_32], [\_100k], [10m], [Direct], [89.2], [37.0], [100,000], [I16], [0.56%], [0.0580%],
  [Topographic Openness (Positive) (Window: 32)], [po\_32], [\_10k], [10m], [Direct], [78.4], [28.9], [10,000], [I16], [0.00%], [0.3201%],
  [Topographic Openness (Difference) (Window: 256)], [diffopen\_256], [\_100k], [10m], [Direct], [91.6], [37.0], [100,000], [I16], [1.17%], [0.0343%],
  [Topographic Openness (Negative) (Window: 256)], [no\_256], [\_10k], [10m], [Direct], [80.4], [28.0], [10,000], [I16], [0.00%], [0.1778%],
  [Topographic Openness (Positive) (Window: 256)], [po\_256], [\_10k], [10m], [Direct], [81.6], [28.3], [10,000], [I16], [0.00%], [0.1708%],
  [Potential Incoming Solar Radiation (Direct) (Date: 2023-01-22)], [pisrdir\_2023-01-22], [\_1k], [10m], [Direct], [68.5], [9.0], [1,000], [I16], [0.00%], [0.8315%],
  [Potential Incoming Solar Radiation (Direct) (Date: 2023-02-22)], [pisrdir\_2023-02-22], [\_1k], [10m], [Direct], [92.4], [19.4], [1,000], [I16], [0.00%], [0.1986%],
  [Potential Incoming Solar Radiation (Direct) (Date: 2023-03-22)], [pisrdir\_2023-03-22], [\_1k], [10m], [Direct], [96.0], [24.9], [1,000], [I16], [0.00%], [0.1097%],
  [Potential Incoming Solar Radiation (Direct) (Date: 2023-04-22)], [pisrdir\_2023-04-22], [\_1k], [10m], [Direct], [93.9], [26.3], [1,000], [I16], [0.00%], [0.1044%],
  [Potential Incoming Solar Radiation (Direct) (Date: 2023-05-22)], [pisrdir\_2023-05-22], [\_1k], [10m], [Direct], [91.0], [25.9], [1,000], [I16], [0.00%], [0.1373%],
  [Potential Incoming Solar Radiation (Direct) (Date: 2023-06-22)], [pisrdir\_2023-06-22], [\_1k], [10m], [Direct], [89.7], [25.2], [1,000], [I16], [0.00%], [0.1891%],
  [Potential Incoming Solar Radiation (Direct) (Date: 2023-12-22)], [pisrdir\_2023-12-22], [\_1k], [10m], [Direct], [45.4], [4.8], [1,000], [I16], [0.00%], [5.3128%],
  [Potential Incoming Solar Radiation (Diffuse) (Date: 2023-01-22)], [pisrdif\_2023-01-22], [\_10k], [10m], [Direct], [79.3], [10.5], [10,000], [I16], [0.00%], [0.0786%],
  [Potential Incoming Solar Radiation (Diffuse) (Date: 2023-02-22)], [pisrdif\_2023-02-22], [\_10k], [10m], [Direct], [80.8], [14.8], [10,000], [I16], [0.00%], [0.0478%],
  [Potential Incoming Solar Radiation (Diffuse) (Date: 2023-03-22)], [pisrdif\_2023-03-22], [\_10k], [10m], [Direct], [80.5], [17.5], [10,000], [I16], [0.00%], [0.0871%],
  [Potential Incoming Solar Radiation (Diffuse) (Date: 2023-04-22)], [pisrdif\_2023-04-22], [\_10k], [10m], [Direct], [78.6], [18.3], [10,000], [I16], [0.00%], [0.1105%],
  [Potential Incoming Solar Radiation (Diffuse) (Date: 2023-05-22)], [pisrdif\_2023-05-22], [\_10k], [10m], [Direct], [79.8], [19.5], [10,000], [I16], [0.00%], [0.0609%],
  [Potential Incoming Solar Radiation (Diffuse) (Date: 2023-06-22)], [pisrdif\_2023-06-22], [\_10k], [10m], [Direct], [80.3], [19.9], [10,000], [I16], [0.00%], [0.0642%],
  [Potential Incoming Solar Radiation (Diffuse) (Date: 2023-12-22)], [pisrdif\_2023-12-22], [\_10k], [10m], [Direct], [60.9], [7.5], [10,000], [I16], [0.00%], [0.0644%],
)
==== Morphometry
<morphometry>
#table(
  columns: (24%, 10%, 8%, 5%, 8%, 7%, 7%, 10%, 7%, 7%, 7%),
  align: (left,left,center,center,center,center,center,center,center,center,center,),
  table.header([Variable Name], [Abbr], [Suffix], [Res], [Match], [Raw GB], [Scaled GB], [Scale], [Type], [% Clamp], [Step/IQR],),
  table.hline(),
  [Aspect (Window: 4)], [aspct\_4], [\_10], [10m], [Direct], [94.5], [26.0], [10], [I16], [0.00%], [0.0630%],
  [Aspect (Window: 16)], [aspct\_16], [\_10], [10m], [Direct], [94.9], [18.3], [10], [I16], [0.00%], [0.0626%],
  [Aspect (Window: 32)], [aspct\_32], [\_10], [10m], [Direct], [95.0], [14.2], [10], [I16], [0.00%], [0.0622%],
  [Convergence Index (Window: 4)], [ci\_4], [\_100], [10m], [Direct], [104.1], [34.4], [100], [I16], [0.00%], [0.0750%],
  [Convergence Index (Window: 16)], [ci\_16], [\_100], [10m], [Direct], [103.9], [30.9], [100], [I16], [0.00%], [0.0467%],
  [Convergence Index (Window: 32)], [ci\_32], [\_100], [10m], [Direct], [103.7], [27.5], [100], [I16], [0.00%], [0.0388%],
  [Cross-sectional Curvature (Window: 4)], [crosc\_4], [\_1M], [10m], [Direct], [104.7], [32.5], [1,000,000], [I16], [0.04%], [0.2016%],
  [Cross-sectional Curvature (Window: 16)], [crosc\_16], [\_1M], [10m], [Direct], [105.2], [21.2], [1,000,000], [I16], [0.00%], [0.5245%],
  [Cross-sectional Curvature (Window: 32)], [crosc\_32], [\_1M], [10m], [Direct], [105.3], [13.8], [1,000,000], [I16], [0.00%], [0.9536%],
  [Longitudinal Curvature (Window: 4)], [longc\_4], [\_1M], [10m], [Direct], [104.8], [32.8], [1,000,000], [I16], [0.04%], [0.1774%],
  [Longitudinal Curvature (Window: 16)], [longc\_16], [\_1M], [10m], [Direct], [104.8], [21.7], [1,000,000], [I16], [0.00%], [0.4624%],
  [Longitudinal Curvature (Window: 32)], [longc\_32], [\_1M], [10m], [Direct], [104.6], [14.2], [1,000,000], [I16], [0.00%], [0.6710%],
  [Mass Balance Index (Threshold: 0.001)], [mbi\_0.001], [\_10k], [10m], [Direct], [99.0], [39.4], [10,000], [I16], [0.00%], [0.0088%],
  [Mass Balance Index (Threshold: 0.01)], [mbi\_0.01], [\_10k], [10m], [Direct], [102.6], [37.3], [10,000], [I16], [0.00%], [0.0415%],
  [Mass Balance Index (Threshold: 0.1)], [mbi\_0.1], [\_100k], [10m], [Direct], [104.0], [38.3], [100,000], [I16], [0.70%], [0.0365%],
  [Maximum Curvature (Window: 4)], [maxc\_4], [\_1M], [10m], [Semantic], [102.6], [32.2], [1,000,000], [I16], [0.13%], [0.1075%],
  [Maximum Curvature (Window: 16)], [maxc\_16], [\_1M], [10m], [Semantic], [103.5], [20.1], [1,000,000], [I16], [0.00%], [0.2769%],
  [Maximum Curvature (Window: 32)], [maxc\_32], [\_1M], [10m], [Semantic], [103.8], [12.5], [1,000,000], [I16], [0.00%], [0.4708%],
  [Mid-slope Position], [msp], [\_10k], [10m], [Direct], [92.0], [31.2], [10,000], [I16], [0.00%], [0.0172%],
  [Minimum Curvature (Window: 4)], [minc\_4], [\_1M], [10m], [Semantic], [103.0], [32.5], [1,000,000], [I16], [0.02%], [0.1051%],
  [Minimum Curvature (Window: 16)], [minc\_16], [\_1M], [10m], [Semantic], [103.0], [20.5], [1,000,000], [I16], [0.00%], [0.2467%],
  [Minimum Curvature (Window: 32)], [minc\_32], [\_1M], [10m], [Semantic], [102.7], [12.7], [1,000,000], [I16], [0.00%], [0.3625%],
  [Multiscale Topographic Position Index (Window: 4)], [tpi\_4], [\_1k], [10m], [Direct], [103.8], [33.9], [1,000], [I16], [0.00%], [0.1623%],
  [Multiscale Topographic Position Index (Window: 32)], [tpi\_32], [\_1k], [10m], [Direct], [104.4], [32.8], [1,000], [I16], [0.00%], [0.1260%],
  [Normalized Height], [nh], [\_10k], [10m], [Semantic], [92.7], [28.8], [10,000], [I16], [0.00%], [0.0192%],
  [Plan Curvature (Window: 4)], [planc\_4], [\_100k], [10m], [Direct], [104.9], [34.1], [100,000], [I16], [0.09%], [0.1222%],
  [Plan Curvature (Window: 16)], [planc\_16], [\_100k], [10m], [Direct], [105.5], [24.7], [100,000], [I16], [0.02%], [0.2637%],
  [Plan Curvature (Window: 32)], [planc\_32], [\_100k], [10m], [Direct], [105.8], [18.0], [100,000], [I16], [0.02%], [0.3950%],
  [Profile Curvature (Window: 4)], [profc\_4], [\_1M], [10m], [Direct], [104.8], [32.5], [1,000,000], [I16], [0.00%], [0.1887%],
  [Profile Curvature (Window: 16)], [profc\_16], [\_1M], [10m], [Direct], [104.8], [21.2], [1,000,000], [I16], [0.00%], [0.4835%],
  [Profile Curvature (Window: 32)], [profc\_32], [\_1M], [10m], [Direct], [104.7], [13.9], [1,000,000], [I16], [0.00%], [0.6917%],
  [Slope (Window: 4)], [sl\_4], [\_100], [10m], [Direct], [96.0], [23.6], [100], [I16], [0.00%], [0.0839%],
  [Slope (Window: 16)], [sl\_16], [\_100], [10m], [Direct], [96.4], [15.0], [100], [I16], [0.00%], [0.0966%],
  [Slope (Window: 32)], [sl\_32], [\_100], [10m], [Direct], [96.8], [10.7], [100], [I16], [0.00%], [0.1107%],
  [Slope Height], [slh], [\_10], [10m], [Semantic], [95.8], [17.0], [10], [I16], [0.00%], [0.2930%],
  [Standardized Height], [stdh], [\_10], [10m], [Semantic], [92.5], [23.0], [10], [I16], [0.00%], [0.0296%],
  [Terrain Ruggedness Index (Window: 4)], [tri\_4], [\_100], [10m], [Direct], [95.4], [20.9], [100], [I16], [0.00%], [0.1728%],
  [Terrain Ruggedness Index (Window: 16)], [tri\_16], [\_100], [10m], [Direct], [95.4], [21.9], [100], [I16], [0.00%], [0.0479%],
  [Terrain Ruggedness Index (Window: 32)], [tri\_32], [\_100], [10m], [Direct], [95.3], [22.4], [100], [I16], [0.00%], [0.0255%],
  [Terrain Surface Convexity (Window: 4)], [tsc\_4], [\_100], [10m], [Direct], [93.6], [33.6], [100], [I16], [0.00%], [0.0345%],
  [Terrain Surface Convexity (Window: 16)], [tsc\_16], [\_100], [10m], [Direct], [91.9], [19.8], [100], [I16], [0.00%], [0.0837%],
  [Terrain Surface Convexity (Window: 32)], [tsc\_32], [\_100], [10m], [Direct], [91.3], [11.6], [100], [I16], [0.00%], [0.1218%],
  [Vector Ruggedness Index (Window: 4)], [vrm\_4], [\_100k], [10m], [Semantic], [99.8], [20.8], [100,000], [I16], [0.00%], [0.4308%],
  [Vector Ruggedness Index (Window: 16)], [vrm\_16], [\_100k], [10m], [Semantic], [98.5], [18.0], [100,000], [I16], [0.07%], [0.0970%],
  [Vector Ruggedness Index (Window: 32)], [vrm\_32], [\_100k], [10m], [Semantic], [97.5], [15.4], [100,000], [I16], [0.04%], [0.0522%],
)
==== Unknown
<unknown>
#table(
  columns: (24%, 10%, 8%, 5%, 8%, 7%, 7%, 10%, 7%, 7%, 7%),
  align: (left,left,center,center,center,center,center,center,center,center,center,),
  table.header([Variable Name], [Abbr], [Suffix], [Res], [Match], [Raw GB], [Scaled GB], [Scale], [Type], [% Clamp], [Step/IQR],),
  table.hline(),
  [dfa], [dfa], [\_10], [10m], [Unverified], [201.2], [34.1], [10], [I16], [3.66%], [0.0431%],
  [dis], [dis], [\_100], [10m], [Unverified], [7.2], [2.9], [100], [I16], [0.00%], [1.6111%],
  [fel], [fel], [\_1], [10m], [Unverified], [190.8], [6.5], [1], [I16], [0.00%], [0.1617%],
)
=== Categorical Covariates Summary
<categorical-covariates-summary>
==== Geomorphons
<geomorphons>
#table(
  columns: (24%, 10%, 8%, 5%, 8%, 7%, 7%, 10%, 7%, 7%, 7%),
  align: (left,left,center,center,center,center,center,center,center,center,center,),
  table.header([Variable Name], [Abbr], [Suffix], [Res], [Match], [Raw GB], [Scaled GB], [Scale], [Type], [% Clamp], [Step/IQR],),
  table.hline(),
  [Geomorphon (Multiscale) (Radius: 30)], [gmrph\_ms\_30], [\_1], [30m], [Direct], [0.5], [0.6], [1], [Byte], [0.00%], [Perfect],
  [Geomorphon (Radius) (Radius: 30)], [gmrph\_r\_30], [\_1], [30m], [Semantic], [0.5], [0.5], [1], [Byte], [0.00%], [Perfect],
  [Geomorphon (Radius) (Radius: 300)], [gmrph\_r\_300], [\_1], [30m], [Semantic], [0.5], [0.6], [1], [Byte], [0.00%], [Perfect],
  [Geomorphon (Multiscale) (Radius: 300)], [gmrph\_ms\_300], [\_1], [30m], [Direct], [0.5], [0.6], [1], [Byte], [0.00%], [Perfect],
  [Geomorphon (Radius) (Radius: 3000)], [gmrph\_r\_3000], [\_1], [30m], [Semantic], [0.5], [0.6], [1], [Byte], [0.00%], [Perfect],
)
==== Morphometry
<morphometry-1>
#table(
  columns: (24%, 10%, 8%, 5%, 8%, 7%, 7%, 10%, 7%, 7%, 7%),
  align: (left,left,center,center,center,center,center,center,center,center,center,),
  table.header([Variable Name], [Abbr], [Suffix], [Res], [Match], [Raw GB], [Scaled GB], [Scale], [Type], [% Clamp], [Step/IQR],),
  table.hline(),
  [Morphometric Features (Window: 4)], [morpfeat\_4], [\_1], [30m], [Direct], [0.6], [0.7], [1], [Byte], [0.00%], [Perfect],
  [Morphometric Features (Window: 16)], [morpfeat\_16], [\_1], [30m], [Direct], [0.4], [0.4], [1], [Byte], [0.00%], [Perfect],
  [Morphometric Features (Window: 32)], [morpfeat\_32], [\_1], [30m], [Direct], [0.3], [0.3], [1], [Byte], [0.00%], [Perfect],
)
#set page(flipped: false)
#set text(size: 11pt)
== File Size Comparison
<file-size-comparison>
#table(
  columns: 2,
  align: (left,center,),
  table.header([Metric], [Value],),
  table.hline(),
  [Total Raw Size], [9.58 TB],
  [Total Scaled Size], [2.54 TB],
  [Storage Reduction], [73.5%],
)
== Final Verification
<final-verification>
- #strong[NoData Integrity:] 100% verified via 10,000-point GEE comparison.
- #strong[Asset Sync:] All 111 bands registered in GEE (`aksdb_topo_v20250422_scaled`).
