# Introduction
Since the UX/UI rework, the CSS as been built from the [Vitamin CSS library](https://github.com/Decathlon/vitamin-web/). 
Vitamin is based on [Tailwind CSS](https://tailwindcss.com/docs) this library is very complete and give you access to 170k lines of css classes etc.
But you will never use all the lines it provides and the resulting CSS should be heavy, which impact the page loading performances.

# Build the CSS
The actual CSS as been written using the [SASS preprocessor](https://sass-lang.com/), specifically the Dart Sass implementation.
The result is purged from all unused class by [PurgeCSS](https://purgecss.com/).

You will have to install a node environement and then install SASS and PurgeCSS using NPM

```
npm install -g sass
```

```
npm install -g purgecss
```

After all prerequisite are installed you just have to run the ```build_css_for_prod.sh``` script.