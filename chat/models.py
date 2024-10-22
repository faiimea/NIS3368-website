import os
import uuid
import mimetypes
import pypinyin
from django.db import models
from users.models import User
from django.contrib.auth import get_user_model
from chat.utils import cmds, format_link, get_first_pinyin_letter, \
    validate_file_size, convert_size


commands = cmds()


#################################################################
#                            PROFILE                            #
#################################################################

def profile_media_path(instance, filename):
    user_name = instance.user.username
    upload_path = os.path.join('users', user_name)
    file_path = os.path.join(upload_path, filename)
    media_upload_path = os.path.join('media', upload_path)
    if not os.path.exists(media_upload_path):
        os.makedirs(media_upload_path)
    return file_path

class Profile(models.Model):
    """
    Personal Profile
    """
    about_me = models.TextField(default='There is no Personal Signature here yet. You can add it through settings')
    image = models.ImageField(upload_to=profile_media_path, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    location = models.CharField(max_length=50, default="Unkown")
    
    @property
    def image_url(self):
        if self.image == "":
            return "/media/static_default/{}.png".format(self.user_initial)
        else:
            return self.image.url
        
    @property
    def user_initial(self):
        return self.user.username[0].upper()
    
    def __str__(self):
        return self.user.username
    


#################################################################
#                         CHATROOM                              #
#################################################################

def room_media_path(instance, filename):
    room_name = instance.name
    upload_path = os.path.join('chatrooms', room_name)
    file_path = os.path.join(upload_path, filename)
    media_upload_path = os.path.join('media', upload_path)
    if not os.path.exists(media_upload_path):
        os.makedirs(media_upload_path)
    return file_path
 
class Room(models.Model):
    """
    A flexible and freely accessible space
    """
    name = models.CharField(max_length=128, unique=True)
    show_name = models.CharField(max_length=100, default="Showname")
    owner_name = models.CharField(max_length=128)
    about_room = models.CharField(max_length=128, default="welcome to my chatroom")
    online = models.ManyToManyField(to=get_user_model(), blank=True)
    image = models.ImageField(upload_to=room_media_path, null=True, blank=True)
    
    def get_online_count(self):
        return self.online.count()

    def join(self, user):
        self.online.add(user)
        self.save()

    def leave(self, user):
        self.online.remove(user)
        self.save()

    @property
    def initial(self):
        return self.name[0].upper()
    
    @property
    def image_url(self):
        if self.image == "":
            return "/media/static_default/{}.png".format(self.initial)
        else:
            return self.image.url
    
    def __str__(self):
        return f'{self.name} ({self.get_online_count()})'


#################################################################
#                             TAG                               #
#################################################################

class Tag(models.Model):
    name = models.CharField(max_length=40, unique=True)

    def __str__(self):
        return self.name
  

#################################################################
#                             POST                              #
#################################################################

def post_media_path(instance, filename):
    room_name = instance.belong_room.name
    post_name = instance.title
    upload_path = os.path.join('chatrooms', room_name, 'posts', post_name)
    file_path = os.path.join(upload_path, filename)
    media_upload_path = os.path.join('media', upload_path)
    if not os.path.exists(media_upload_path):
        os.makedirs(media_upload_path)
    return file_path

class Post(models.Model):
    """
    A flexible and freely accessible space
    """
    title = models.CharField(max_length=128)
    show_name = models.CharField(max_length=128,default="Post_Showname")
    author = models.ForeignKey(to=User, on_delete=models.CASCADE)
    author_profile = models.ForeignKey(to=Profile, on_delete=models.CASCADE)
    about_post = models.CharField(max_length=1000, default="The author did not set an introduction to the topic")
    image = models.ImageField(upload_to=post_media_path, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now= True)
    belong_room = models.ForeignKey(to=Room, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag, blank=True)

    @property
    def initial(self):
        return self.title[0].upper()
    
    class Meta:
        ordering = ['-created_on']
        
    @property
    def image_url(self):
        if self.title.startswith('chatting_'):
            return self.belong_room.image_url
        if self.image == "" or self.image is None:
            return "/media/static_default/{}.png".format(self.initial)
        else:
            return self.image.url

    @property
    def all_tags(self):
        if self.tags.all() == "" or self.tags.all() is None:
            return None
        else:
            return self.tags.all()
          
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        

#################################################################
#                       CHATROOM MESSAGE                        #
#################################################################

def room_message_media_path(instance, filename):
    room_name = instance.room.name
    post_name = instance.belong_post.title
    upload_path = os.path.join('chatrooms', room_name, 'posts', post_name)
    file_path = os.path.join(upload_path, filename)
    media_upload_path = os.path.join('media', upload_path)
    if not os.path.exists(media_upload_path):
        os.makedirs(media_upload_path)
    return file_path

class RoomMessage(models.Model):
    """
    Message for Room
    """
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(to=get_user_model(), on_delete=models.CASCADE)
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE)
    belong_post = models.ForeignKey(to=Post, on_delete=models.CASCADE)
    content = models.CharField(max_length=512)
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to=room_message_media_path, null=True, blank=True)

    def __str__(self):
        return f'{self.user.username}: {self.content} [{self.timestamp}]'
    
    def save(self, *args, **kwargs):
        if self.attachment.name:
            validate_file_size(self.attachment)
        super().save(*args, **kwargs)
        
    @property
    def image_url(self):
        profile = Profile.objects.get(user=self.user)
        return profile.image_url

    @property
    def attachment_url(self):
        if self.attachment.name == "" or self.attachment.name is None:
            return ""
        return self.attachment.url
    
    @property
    def attachment_type(self):
        file_type, _ = mimetypes.guess_type(self.attachment.name)
        if file_type.startswith("image"):
            file_type = "image"
        return file_type
    
    @property
    def attachment_name(self):
        if self.attachment.name == "" or self.attachment.name is None:
            return None
        return os.path.basename(self.attachment.name)
        
    @property
    def attachment_size(self):
        try:
            size = os.path.getsize(self.attachment.path)
            return convert_size(size)
        except:
            return 'Unknown Size'
        

#################################################################
#                         FRIEND REQUEST                        #
#################################################################

class Friend_Request(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    from_user = models.ForeignKey(User, related_name='from_user', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='to_user', on_delete=models.CASCADE)
    invite_message = models.CharField(max_length=50)
    groups_name = models.CharField(max_length=50, default="NONE")
    
    @property
    def from_user_profile(self):
        return Profile.objects.get(user=self.from_user)
    
    @property
    def to_user_profile(self):
        return Profile.objects.get(user=self.to_user)
    

#################################################################
#                         FRIEND ROOM                           #
#################################################################

class FriendRoom(models.Model):
    """
    A flexible and freely accessible space
    """
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendroom_user_1')
    user_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendroom_user_2')
    
    def __str__(self):
        return f'FR({self.user_1.username}, {self.user_2.username})'
    

#################################################################
#                        FRIEND MESSAGE                         #
#################################################################

def friend_message_media_path(instance, filename):
    uid = instance.belong_fm.uid
    upload_path = os.path.join('chatfriends', str(uid))
    file_path = os.path.join(upload_path, filename)
    media_upload_path = os.path.join('media', upload_path)
    if not os.path.exists(media_upload_path):
        os.makedirs(media_upload_path)
    return file_path

class FMMessage(models.Model):
    """
    Message for FriendRoom
    """
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(to=get_user_model(), on_delete=models.CASCADE)
    belong_fm = models.ForeignKey(to=FriendRoom, on_delete=models.CASCADE)
    content = models.CharField(max_length=512)
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to=friend_message_media_path, null=True, blank=True)

    def __str__(self):
        return f'{self.user.username}: {self.content} [{self.timestamp}]'
    
    def save(self, *args, **kwargs):
        if self.attachment.name:
            validate_file_size(self.attachment)
        super().save(*args, **kwargs)
       
    @property
    def image_url(self):
        profile = Profile.objects.get(user=self.user)
        return profile.image_url

    @property
    def attachment_url(self):
        if self.attachment.name == "" or self.attachment.name is None:
            return ""
        return self.attachment.url
    
    @property
    def attachment_type(self):
        file_type, _ = mimetypes.guess_type(self.attachment.name)
        if file_type.startswith("image"):
            file_type = "image"
        return file_type
    
    @property
    def attachment_name(self):
        if self.attachment.name == "" or self.attachment.name is None:
            return None
        return os.path.basename(self.attachment.name)
        
    @property
    def attachment_size(self):
        try:
            size = os.path.getsize(self.attachment.path)
            return convert_size(size)
        except:
            return 'Unknown Size'


#################################################################
#                            LINK                               #
#################################################################

class LINK(models.Model):
    url = models.URLField(max_length=100)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(to=get_user_model(), on_delete=models.CASCADE)

    def __str__(self):
        return self.url

    @property
    def initial(self):
        if pypinyin.pinyin(self.name[0]):
            return get_first_pinyin_letter(self.name[0]).upper()
        return self.name[0].upper()

    @property
    def image_url(self):
        if str(self.url).startswith("https://github.com"):
            return "/media/link_image/github_com_.png"
        file_path = format_link(str(self.url))
        file_path = "media/link_image/{}.png".format(file_path)
        if os.path.exists(file_path):
            return "/" + file_path
        else:
            commands.add_download_subprocess(str(self.url), file_path)
            return "/media/static_default/{}.png".format(self.initial)
        

#################################################################
#                            GROUPS                             #
#################################################################

def groups_media_path(instance, filename):
    group_uid = instance.uid
    upload_path = os.path.join('groups', str(group_uid))
    file_path = os.path.join(upload_path, filename)
    media_upload_path = os.path.join('media', upload_path)
    if not os.path.exists(media_upload_path):
        os.makedirs(media_upload_path)
    return file_path

class Groups(models.Model):
    """
    A flexible and freely accessible space
    """
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=128)
    show_name = models.CharField(max_length=128, default="Group_Showname")
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='owner')
    about_group = models.CharField(max_length=128, default="welcome")
    members = models.ManyToManyField(to=User, blank=True, related_name='members')
    image = models.ImageField(upload_to=groups_media_path, null=True, blank=True)

    @property
    def initial(self):
        return self.name[0].upper()

    @property
    def owner_name(self):
        return self.owner.username  

    @property
    def image_url(self):
        if self.image == "":
            return "/media/static_default/{}.png".format(self.initial)
        else:
            return self.image.url
        
    def exist(self, user:User):
        if user in self.members.all():
            return True
        else:
            return False
        
    def __str__(self):
        return f'{self.name}'
    

#################################################################
#                        FRIEND MESSAGE                         #
#################################################################

def groups_message_media_path(instance, filename):
    uid = instance.belong_group.uid
    upload_path = os.path.join('groups', str(uid))
    file_path = os.path.join(upload_path, filename)
    media_upload_path = os.path.join('media', upload_path)
    if not os.path.exists(media_upload_path):
        os.makedirs(media_upload_path)
    return file_path

class GroupMessage(models.Model):
    """
    Message for FriendRoom
    """
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(to=get_user_model(), on_delete=models.CASCADE)
    belong_group = models.ForeignKey(to=Groups, on_delete=models.CASCADE)
    content = models.CharField(max_length=512)
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to=groups_message_media_path, null=True, blank=True)

    def __str__(self):
        return f'{self.user.username}: {self.content} [{self.timestamp}]'
    
    def save(self, *args, **kwargs):
        if self.attachment.name:
            validate_file_size(self.attachment)
        super().save(*args, **kwargs)
       
    @property
    def image_url(self):
        profile = Profile.objects.get(user=self.user)
        return profile.image_url

    @property
    def attachment_url(self):
        if self.attachment.name == "" or self.attachment.name is None:
            return ""
        return self.attachment.url
    
    @property
    def attachment_type(self):
        file_type, _ = mimetypes.guess_type(self.attachment.name)
        if file_type.startswith("image"):
            file_type = "image"
        return file_type
    
    @property
    def attachment_name(self):
        if self.attachment.name == "" or self.attachment.name is None:
            return None
        return os.path.basename(self.attachment.name)
        
    @property
    def attachment_size(self):
        try:
            size = os.path.getsize(self.attachment.path)
            return convert_size(size)
        except:
            return 'Unknown Size'
