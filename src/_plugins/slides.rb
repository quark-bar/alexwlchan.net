# This is a plugin for embedding slide images.
#
# Each image needs to be both an image, and a link to the fullsized image.
#
# To embed a slide, place a Liquid tag of the following form anywhere in a
# source file:
#
#     {% slide docopt 1 %}
#
# You can also use slide_captioned if you want a <figcaption> on the slide
# (e.g. to add image attribution):
#
#     {% slide_captioned docopt 2 %}
#       This slide uses an image from https://example.org/
#     {% endslide_captioned %}
#

module Jekyll
  class SlideTag < Liquid::Tag
    def initialize(tag_name, text, tokens)
      super
      @deck = text.split(" ").first
      @number = text.split(" ").last.to_i
    end

    def render(context)
      path = "/slides/#{@deck}/#{@deck}.#{@number.to_s.rjust(3, '0')}.png"
<<-EOT
<figure class="slide">
  <a href="#{path}"><img src="#{path}"></a>
</figure>
EOT
    end
  end

  class CaptionedSlideBlock < Liquid::Block
    def initialize(tag_name, text, tokens)
      @deck = text.split(" ").first
      @number = text.split(" ").last.to_i
      super
    end

    def render(context)
      site = context.registers[:site]
      converter = site.find_converter_instance(::Jekyll::Converters::Markdown)

      md_content = super.strip
      html_content = converter.convert(md_content)

      path = "/slides/#{@deck}/#{@deck}.#{@number.to_s.rjust(3, '0')}.png"

<<-EOT
<figure class="slide">
  <a href="#{path}"><img src="#{path}"></a>
  <figcaption>#{html_content}</figcaption>
</figure>
EOT
    end
  end
end

Liquid::Template.register_tag('slide', Jekyll::SlideTag)
Liquid::Template.register_tag("slide_captioned", Jekyll::CaptionedSlideBlock)
