import api_functions as af

email = 'pchtsp@gmail.com'
pwd = 'ElMaizMagico'
name = 'pchtsp'

config = dict(email=email, pwd=pwd, name=name)

af.sign_up(**config)
