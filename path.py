import osmnx as ox
import time
import heapq
import math
from datetime import datetime


place_name = "Institut Teknologi Sepuluh Nopember, Surabaya, Indonesia"
print("Loading the ITS campus graph (might take a few seconds)")
G = ox.graph_from_address(place_name, dist=2000, network_type='all')

# -------------- Algorithm --------------
def haversine(lat1, lon1, lat2, lon2):
    # Calculates the straight-line distance across the Earth's surface in meters. Used for the heuristic value for A*
    R = 6371000  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def run_dijkstra(graph, start, target):
    # Custom Dijkstra implementation using a priority queue
    pq = [(0, start)]  # (cumulative_distance, node)
    distances = {start: 0}
    came_from = {start: None}
    explored_edges = []
    visited = set()

    while pq:
        current_dist, u = heapq.heappop(pq)
        
        if u in visited:
            continue
        visited.add(u)

        if u == target:
            break

        # Check all neighboring intersections
        for v, edge_data in graph[u].items():
            # Handle MultiDiGraph by grabbing the shortest road if there are multiple lanes
            weight = min([data.get('length', 1.0) for data in edge_data.values()])
            
            # Record that we searched this current street
            if u != start:
                explored_edges.append((u, v))

            new_dist = current_dist + weight
            if new_dist < distances.get(v, float('inf')):
                distances[v] = new_dist
                came_from[v] = u
                heapq.heappush(pq, (new_dist, v))

    # Reconstruct the final shortest path
    path = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = came_from.get(curr)
    path.reverse()

    if path[0] != start:
        return [], explored_edges  # Path not found

    return path, explored_edges

def run_astar(graph, start, target):
    # Custom A* implementation using the Haversine heuristic.
    target_lat = graph.nodes[target]['y']
    target_lon = graph.nodes[target]['x']

    pq = [(0, 0, start)]  # (f_score, g_score, node)
    g_scores = {start: 0}
    came_from = {start: None}
    explored_edges = []
    visited = set()

    while pq:
        f, current_dist, u = heapq.heappop(pq)
        
        if u in visited:
            continue
        visited.add(u)

        if u == target:
            break

        u_lat = graph.nodes[u]['y']
        u_lon = graph.nodes[u]['x']

        for v, edge_data in graph[u].items():
            weight = min([data.get('length', 1.0) for data in edge_data.values()])
            
            if u != start:
                explored_edges.append((u, v))

            new_dist = current_dist + weight
            if new_dist < g_scores.get(v, float('inf')):
                g_scores[v] = new_dist
                came_from[v] = u
                
                # Calculate the heuristic (straight line to target)
                v_lat = graph.nodes[v]['y']
                v_lon = graph.nodes[v]['x']
                h_score = haversine(v_lat, v_lon, target_lat, target_lon)
                f_score = new_dist + h_score
                
                heapq.heappush(pq, (f_score, new_dist, v))

    # Reconstruct the final shortest path
    path = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = came_from.get(curr)
    path.reverse()

    if path[0] != start:
        return [], explored_edges

    return path, explored_edges

# -------------- Visualization --------------
def write_log(filename, algo_name, start_time, end_time, total_ms, path_len):
    # Writes the required .txt log file with precise execution times.
    with open(filename, 'w') as f:
        f.write(f"--- Testing Log ---\n")
        f.write(f"Algorithm: {algo_name}\n")
        f.write(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}\n")
        f.write(f"End Time:   {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')}\n")
        f.write(f"Total Execution: {total_ms:.4f} ms\n")
        f.write(f"Intersections Traversed: {path_len}\n")
    print(f"  Log saved: {filename}")

def create_algorithm_map(graph, path, explored_edges, filename):
    # Draws the explored search space and final path.
    print(f"  Drawing map: {filename}...")
    
    edges_gdf = ox.graph_to_gdfs(graph, nodes=False)
    explored_set = set(explored_edges)
    
    # Filter the map to only show roads the algorithm actively checked
    valid_indices = [(u, v, k) for u, v, k in edges_gdf.index if (u, v) in explored_set or (v, u) in explored_set]
    
    if valid_indices:
        explored_gdf = edges_gdf.loc[valid_indices]
        # Draw explored area in translucent blue
        m = explored_gdf.explore(color="blue", style_kwds={"weight": 3, "opacity": 0.3}, tiles="CartoDB positron")
    else:
        m = edges_gdf.explore(color="lightgray", style_kwds={"weight": 1}, tiles="CartoDB positron")

    # Overlay the final calculated route in thick red
    if path:
        route_gdf = ox.routing.route_to_gdf(graph, path, weight='length')
        m = route_gdf.explore(m=m, color="red", style_kwds={"weight": 6})
        
    m.save(filename)

# -------------- Execution --------------
print("\n=== Dijkstra and A* Traversing ITS Map Performance Test ===")
print("Type a specific location (e.g., 'Asrama Mahasiswa ITS', 'Rektorat ITS, Surabaya')")
print("Type 'exit' to quit.\n")

def get_valid_node(prompt_text, graph):
    while True:
        user_input = input(prompt_text).strip()
        
        if user_input.lower() == 'exit':
            exit()
            
        if not user_input:
            continue
            
        print(f"  Searching map for '{user_input}'...")
        
        try:
            coords = ox.geocode(user_input)
            node = ox.distance.nearest_nodes(graph, X=coords[1], Y=coords[0])
            print(f"  ✅ Found! Snapped to Node ID: {node}")
            return node 
        except Exception:
            print("  ❌ Address not found. Try adding 'ITS' or 'Surabaya' to be more specific.\n")


# Get inputs
start_node = get_valid_node("Enter Pickup Location: ", G)
print("-" * 40)
end_node = get_valid_node("Enter Drop-off Location: ", G)

print(f"\n[System Success] Ready to route from Node {start_node} -> Node {end_node}")

# --- Run Dijkstra ---
print("\n[1/2] Running Dijkstra...")
dt_start_d = datetime.now()
start_t_d = time.perf_counter()

path_d, explored_d = run_dijkstra(G, start_node, end_node)

end_t_d = time.perf_counter()
dt_end_d = datetime.now()
time_d_ms = (end_t_d - start_t_d) * 1000

print(f"> Dijkstra finished in {time_d_ms:.3f} ms. Route is {len(path_d)} intersections long.")
write_log("dijkstra_log.txt", "Dijkstra", dt_start_d, dt_end_d, time_d_ms, len(path_d))
create_algorithm_map(G, path_d, explored_d, "dijkstra_route.html")

# --- Run A* ---
print("\n[2/2] Running A*...")
dt_start_a = datetime.now()
start_t_a = time.perf_counter()

path_a, explored_a = run_astar(G, start_node, end_node)

end_t_a = time.perf_counter()
dt_end_a = datetime.now()
time_a_ms = (end_t_a - start_t_a) * 1000

print(f"> A* finished in {time_a_ms:.3f} ms. Route is {len(path_a)} intersections long.")
write_log("astar_log.txt", "A-Star", dt_start_a, dt_end_a, time_a_ms, len(path_a))
create_algorithm_map(G, path_a, explored_a, "astar_route.html")

print("\n✅ Testing run complete! Check your folder for the text logs and HTML maps ✅")
