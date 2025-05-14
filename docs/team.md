<script setup>
import { VPTeamMembers } from 'vitepress/theme'

const members = [
  {
    avatar: 'https://media.licdn.com/dms/image/v2/D4D03AQHox-tilc7cYw/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1680781718271?e=1752710400&v=beta&t=X-BU8PvHbGzxboZoByiAq-XM5cj7P-50AL7RInt6d0I',
    name: 'Estefania Nuñez',
    title: 'Account Manager',
    links: [
      { icon: 'linkedin', link: 'https://www.linkedin.com/in/estefania-nu%C3%B1ez-97b6b8244/' }
    ]
  },{
    avatar: 'https://media.licdn.com/dms/image/v2/D4D03AQFAZijewoXO3A/profile-displayphoto-shrink_400_400/B4DZYR6Ii_HwAk-/0/1744057174674?e=1752710400&v=beta&t=3W6MLAsI000muc5cN2r8jkzQLkpo4vPihhGGWtYzveI',
    name: 'Iva Rumora',
    title: 'Product Manager',
    links: [
      { icon: 'linkedin', link: 'https://www.linkedin.com/in/irumora/' }
    ]
  },{
    avatar: 'https://media.licdn.com/dms/image/v2/C4D03AQENPuCOF4nuOA/profile-displayphoto-shrink_100_100/profile-displayphoto-shrink_100_100/0/1529583600854?e=1752710400&v=beta&t=_9nNHn-Q3RUE9yccLBAspO565bOinsf2BaqGfE5EmaA',
    name: 'Gustavo Brian',
    title: 'Creator',
    links: [
      { icon: 'github', link: 'https://github.com/gbrian' },
      { icon: 'linkedin', link: 'https://www.linkedin.com/in/gustavo-brian-n-s-a5710912/' }
    ]
  },
]
</script>

# Our Team

Say hello to our awesome team.

<VPTeamMembers size="small" :members />