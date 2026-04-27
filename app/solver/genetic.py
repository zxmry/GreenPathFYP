"""Genetic Algorithm solver for the Travelling Salesman Problem (TSP)."""

import random


class GeneticOptimizer:
    def __init__(
        self,
        distance_matrix,
        pop_size=50,
        elite_size=10,
        mutation_rate=0.01,
        generations=100,
    ):
        self.matrix = distance_matrix
        self.pop_size = pop_size
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.generations = generations
        self.num_cities = len(distance_matrix)

    def create_route(self):
        """Creates a random route (permutation of city indices)."""
        return random.sample(range(self.num_cities), self.num_cities)

    def initial_population(self):
        """Creates the starting population of random routes."""
        return [self.create_route() for _ in range(self.pop_size)]

    def route_distance(self, route):
        distance = 0
        for i in range(len(route)):
            from_city = route[i]
            to_city = route[i + 1] if i + 1 < len(route) else route[0]

            segment_dist = self.matrix[from_city][to_city]

            # If OSRM returns None (unreachable), treat it as infinite distance
            if segment_dist is None:
                segment_dist = 1000000000  # A very large number (1 billion meters)

            distance += segment_dist

        return distance

    def rank_routes(self, population):
        """Sorts population by distance (shortest first)."""
        fitness_results = {}
        for i in range(len(population)):
            fitness_results[i] = self.route_distance(population[i])

        return sorted(fitness_results.items(), key=lambda x: x[1])

    def selection(self, pop_ranked):
        """Tournament selection: simpler and often better than roulette wheel."""
        selection_results = []

        # Elitism: Automatically keep the best routes
        for i in range(self.elite_size):
            selection_results.append(pop_ranked[i][0])

        # Fill the rest using tournament selection
        for _ in range(len(pop_ranked) - self.elite_size):
            pick_1 = random.choice(pop_ranked)[0]
            pick_2 = random.choice(pop_ranked)[0]
            winner = (
                pick_1
                if self.route_distance(self.population[pick_1])
                < self.route_distance(self.population[pick_2])
                else pick_2
            )
            selection_results.append(winner)

        return selection_results

    def crossover(self, parent1, parent2):
        """Ordered Crossover (OX1) - Critical for TSP."""
        child = [None] * self.num_cities

        start_pos = random.randint(0, self.num_cities - 1)
        end_pos = random.randint(0, self.num_cities - 1)

        if start_pos > end_pos:
            start_pos, end_pos = end_pos, start_pos

        # Copy a slice from parent1
        for i in range(start_pos, end_pos + 1):
            child[i] = parent1[i]

        # Fill empty slots with cities from parent2 in order
        p2_index = 0
        for i in range(self.num_cities):
            if child[i] is None:
                while parent2[p2_index] in child:
                    p2_index += 1
                child[i] = parent2[p2_index]

        return child

    def mutate(self, route):
        """Swap Mutation: Swap two cities to introduce variation."""
        for i in range(len(route)):
            if random.random() < self.mutation_rate:
                swap_with = int(random.random() * len(route))
                route[i], route[swap_with] = route[swap_with], route[i]
        return route

    def next_generation(self, current_pop):
        # 1. Rank Routes
        self.population = current_pop  # Store for selection reference
        pop_ranked = self.rank_routes(current_pop)

        # 2. Selection
        selection_ids = self.selection(pop_ranked)
        mating_pool = [current_pop[i] for i in selection_ids]

        # 3. Crossover (Breeding)
        children = []
        # Keep elites exactly as they are (no crossover)
        for i in range(self.elite_size):
            children.append(mating_pool[i])

        # Breed the rest
        pool = random.sample(mating_pool, len(mating_pool))
        for i in range(len(mating_pool) - self.elite_size):
            child = self.crossover(pool[i], pool[len(mating_pool) - i - 1])
            children.append(child)

        # 4. Mutation
        next_gen = []
        for i in range(len(children)):
            # Don't mutate elites to preserve the best solution found so far
            if i < self.elite_size:
                next_gen.append(children[i])
            else:
                next_gen.append(self.mutate(children[i]))

        return next_gen

    def solve(self):
        """Main execution function."""
        pop = self.initial_population()

        for _ in range(self.generations):
            pop = self.next_generation(pop)

        ranked = self.rank_routes(pop)
        best_route_index = ranked[0][0]
        best_route = pop[best_route_index]
        best_distance = ranked[0][1]

        return best_route, best_distance

