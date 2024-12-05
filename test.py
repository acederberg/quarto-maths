"""
pandoc 
  to: html
  output-file: live.html
  standalone: true
  embed-resources: false
  title-prefix: acederberg.io
  section-divs: true
  html-math-method: mathjax
  wrap: none
  default-image-extension: png
  toc: true
  toc-depth: 3
  
metadata
  document-css: false
  link-citations: true
  date-format: long
  lang: en
  jupyter: python3
  theme:
    light:
      - cosmo
      - ./themes/*.css
      - ./themes/*.scss
      - cyborg
      - ./terminal.scss
  author:
    - name: Adrian Cederberg
      url: acederberg.io
      email: adrn.cederberg123@gmail.com
  title: ''
  navbar: false
  page-layout: full
"""
