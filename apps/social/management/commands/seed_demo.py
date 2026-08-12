from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Follow
from apps.social.models import Comment, Like, Post

User = get_user_model()


CREATORS = [
    {"username": "maialuz", "display_name": "Maia Luz", "specialty": "photography", "bio": "Fotografia de moda, luz natural e histórias com movimento.", "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=300&q=80"},
    {"username": "juno.studio", "display_name": "Juno Studio", "specialty": "nail-art", "bio": "Unhas como pequenas superfícies de arte.", "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80"},
    {"username": "caio.cor", "display_name": "Caio Cor", "specialty": "painting", "bio": "Pintura, mural e cor no espaço público.", "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80"},
    {"username": "lia.forma", "display_name": "Lia Forma", "specialty": "design", "bio": "Identidades para gente que tem algo a dizer.", "avatar_url": "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=300&q=80"},
]

POSTS = [
    ("maialuz", "A luz chegou antes da ideia — e eu só precisei acompanhar. Um recorte do ensaio de hoje.", "photography", "https://images.unsplash.com/photo-1504198453319-5ce911bafcde?auto=format&fit=crop&w=1200&q=85", "fotografia,luz,processo"),
    ("juno.studio", "Textura translúcida, metal e um pouco de exagero. Qual detalhe você levaria?", "beauty", "https://images.unsplash.com/photo-1604654894610-df63bc536371?auto=format&fit=crop&w=1200&q=85", "nailart,beleza,textura"),
    ("caio.cor", "Estudo para um mural sobre movimento e território. Ainda dá para ver as decisões mudando no papel.", "art", "https://images.unsplash.com/photo-1547891654-e66ed7ebb968?auto=format&fit=crop&w=1200&q=85", "pintura,mural,processo"),
    ("lia.forma", "Abrindo duas vagas para identidade visual em setembro. Procuro projetos de moda, música e cultura independente.", "opportunity", "https://images.unsplash.com/photo-1558655146-9f40138edfeb?auto=format&fit=crop&w=1200&q=85", "design,oportunidade,branding"),
]


class Command(BaseCommand):
    help = "Cria dados demonstrativos locais da PULSO."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("A carga demonstrativa só pode ser executada com DEBUG=True.")

        users = {}
        for data in CREATORS:
            user, _ = User.objects.get_or_create(username=data["username"], defaults={"email": f"{data['username'].replace('.', '')}@pulso.demo"})
            user.set_password("PulsoDemo!123")
            user.save()
            for field in ("display_name", "specialty", "bio", "avatar_url"):
                setattr(user.profile, field, data[field])
            user.profile.save()
            users[user.username] = user
        for username, text, category, image, tags in POSTS:
            Post.objects.get_or_create(author=users[username], body=text, defaults={"category": category, "image_url": image, "tags": tags})
        for follower in users.values():
            for following in users.values():
                if follower != following:
                    Follow.objects.get_or_create(follower=follower, following=following)
        posts = list(Post.objects.all())
        for index, post in enumerate(posts):
            for user in list(users.values())[: index + 1]:
                Like.objects.get_or_create(user=user, post=post)
            Comment.objects.get_or_create(author=list(users.values())[-1], post=post, body="Essa escolha ficou muito forte — quero ver o processo inteiro.")
        self.stdout.write(self.style.SUCCESS("Demo criada. Contas usam a senha PulsoDemo!123"))
