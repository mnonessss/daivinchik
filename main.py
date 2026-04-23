from fastapi import FastAPI
from interactions.router import router as interactions_router
from profiles.router import router as profiles_router
from ranking.router import router as ranking_router
from users.router import router as users_router

app = FastAPI()

app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(interactions_router)
app.include_router(ranking_router)
