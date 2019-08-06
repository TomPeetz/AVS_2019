
#include <string.h>
#include <stdint.h>

int check_trip(const uint64_t start_edge, const uint64_t end_edge, const uint64_t len_net_edges, const uint64_t *const *const net_edges) {
    
    uint_fast8_t v[len_net_edges];
    memset(v, 0, len_net_edges * sizeof(uint_fast8_t));
    uint_fast8_t l[len_net_edges];
    memset(l, 0, len_net_edges * sizeof(uint_fast8_t));
    
    const uint64_t size = len_net_edges + 1;
    uint64_t q[size];
    uint64_t head = 0;
    uint64_t tail = 0;
    
    q[tail++] = start_edge;
    
    while (head != tail) {
        const uint64_t cur_edge = q[head];
        head = (head+1) % size;
        v[cur_edge] = 1;
        
        const uint64_t to_edges_len = net_edges[cur_edge][0];
        for (uint64_t i=1; i < to_edges_len; ++i) {
            
            const uint64_t ex_id = net_edges[cur_edge][i];
            
            if (v[ex_id]) {
                continue;
            }
            
            if (l[ex_id]) {
                continue;
            }
            
            if (ex_id == end_edge) {
                return 1;
            }
            
            q[tail] = ex_id;
            tail = (tail+1) % size;
            
            l[ex_id] = 1;
        }
    }
    
    return 0;
}
