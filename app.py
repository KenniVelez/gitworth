from flask import Flask, jsonify
import requests
from flask_caching import Cache
import os

app = Flask("gitworth")

# Configure caching (stores results for 5 minutes)
app.config["CACHE_TYPE"] = "simple"
cache = Cache(app)

GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com/users/")
GITHUB_REPOS_URL = os.getenv("GITHUB_REPOS_URL", "https://api.github.com/users/{}/repos")

def calculate_gitworth(profile_data: dict, repos_data: list) -> float:
    """
    Calculate the gitworth score based on user's profile and repository data.

    Parameters:
    - profile_data (dict): A dictionary containing the user's GitHub profile data.
    - repos_data (list): A list of dictionaries, each containing data for one of the user's repositories.

    Returns:
    - float: The normalized gitworth score, ranging from 0 to 100.
    """
    followers = profile_data.get("followers", 0)
    public_repos = profile_data.get("public_repos", 0)
    stars = sum(repo.get("stargazers_count", 0) for repo in repos_data)
    forks = sum(repo.get("forks_count", 0) for repo in repos_data)
    
    raw_score = (followers * 3) + (public_repos * 2) + (stars * 4) + (forks * 1)

    # Normalize score to a scale of 0-100
    MAX_POSSIBLE_SCORE = 10000  # Adjust based on expected high values
    normalized_score = min(100, (raw_score / MAX_POSSIBLE_SCORE) * 100)
    
    return round(normalized_score, 2)

@cache.memoize(300)  # Cache results for 5 minutes
@app.route("/profile/<username>", methods=["GET"])
def get_profile(username):
    try:
        profile_response = requests.get(GITHUB_API_URL + username)
        repos_response = requests.get(GITHUB_REPOS_URL.format(username))
        
        if profile_response.status_code == 200 and repos_response.status_code == 200:
            profile_data = profile_response.json()
            repos_data = repos_response.json()
            
            gitworth_score = calculate_gitworth(profile_data, repos_data)

            # Format response with only key data
            return jsonify({
                "username": profile_data.get("login"),
                "name": profile_data.get("name"),
                "followers": profile_data.get("followers"),
                "public_repos": profile_data.get("public_repos"),
                "stars_received": sum(repo.get("stargazers_count", 0) for repo in repos_data),
                "forks_received": sum(repo.get("forks_count", 0) for repo in repos_data),
                "gitworth_score": gitworth_score
            })
        elif profile_response.status_code == 403:
            return jsonify({"error": "GitHub API rate limit exceeded. Try again later."}), 403
        else:
            return jsonify({"error": "User not found"}), 404
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
