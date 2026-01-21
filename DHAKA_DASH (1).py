from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math
import random
import time
WIN_W, WIN_H = 1600, 900
LANES = [-7.5, 0.0, 7.8]
ROAD_W = 21
GRASS_LIMIT = 105
FIRE_DELAY = 0.25
BOMB_DELAY = 0.9

class Transform:
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z
        self.current_lane = 1
        self.desired_lane = 1

class Health:
    def __init__(self, max_val):
        self.max_val = max_val
        self.val = max_val
        self.alive = True
    
    def damage(self, amt):
        self.val = max(0, self.val - amt)
        self.alive = self.val > 0
        return self.alive
    
    def restore(self, amt):
        self.val = min(self.max_val, self.val + amt)

class Ammonation:
    def __init__(self):
        self.fire_time = 0
        self.bomb_time = 0
        self.ready = True

class Motion:
    def __init__(self, vx=0, vy=0, vz=0):
        self.vx, self.vy, self.vz = vx, vy, vz

class Visuals:
    def __init__(self, rgb, dimensions):
        self.rgb = rgb
        self.dimensions = dimensions
        self.show = True

class GObject:
    next_id = 0
    
    def __init__(self, obj_type):
        self.id = GObject.next_id
        GObject.next_id += 1
        self.obj_type = obj_type
        self.parts = {}
        self.enabled = True
    
    def attach(self, part_name, part):
        self.parts[part_name] = part
        return self
    
    def fetch(self, part_name):
        return self.parts.get(part_name)

class Objectreg:
    def __init__(self):
        self.items = []
        self.unused = []
    
    def create(self, obj_type):
        if self.unused:
            obj = self.unused.pop()
            obj.enabled = True
            obj.obj_type = obj_type
            return obj
        obj = GObject(obj_type)
        self.items.append(obj)
        return obj
    
    def remove(self, obj):
        obj.enabled = False
        obj.parts.clear()
        self.unused.append(obj)
    
    def filter_type(self, obj_type):
        return [o for o in self.items if o.enabled and o.obj_type == obj_type]
    
    def all_active(self):
        return [o for o in self.items if o.enabled]

class Phase:
    def __init__(self, world):
        self.world = world
    
    def on_enter(self):
        pass
    
    def on_exit(self):
        pass
    
    def tick(self, elapsed):
        pass
    
    def paint(self):
        pass

class Menu(Phase):
    def on_enter(self):
        self.mode_choice = "Normal"
    
    def tick(self, elapsed):
        pass
    
    def paint(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, WIN_W, 0, WIN_H)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        self._paint_string(WIN_W//2 - 120, WIN_H//2 + 110, "DHAKA DASH", (0, 0, 0))
        self._paint_string(WIN_W//2 - 160, WIN_H//2, f"MODE: {self.mode_choice}", (0.95, 0.95, 0.95))
        self._paint_string(WIN_W//2 - 260, WIN_H//2 - 55, "1=Easy / 2=Normal / 3=Hard", (0.95, 0.95, 0.95))
        self._paint_string(WIN_W//2 - 160, WIN_H//2 - 110, "TAB to begin", (0.95, 0.95, 0.95))
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
    
    def _paint_string(self, x, y, text, rgb):
        glColor3f(*rgb)
        glRasterPos2f(x, y)
        for c in text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
    
    def process_key(self, key):
        if key == b'\t':
            return 'RUNNING'
        elif key == b'1':
            self.mode_choice = "Easy"
        elif key == b'2':
            self.mode_choice = "Normal"
        elif key == b'3':
            self.mode_choice = "Hard"
        return None

class Running(Phase):
    def on_enter(self):
        self.build_world()
    
    def build_world(self):
        self.world.registry = Objectreg()
        hero = self.world.registry.create('HERO')
        hero.attach('transform', Transform(0, 0.5, 0))
        hero.attach('vitality', Health(100))
        hero.attach('armament', Ammonation())
        hero.attach('visuals', Visuals((0.25, 0.55, 0.95), [1.3, 0.65, 2.1]))
        self.world.hero = hero
        
        for i in range(6):
            self._create_foe(-80 - i * 80)
        for i in range(18):
            self._create_barrier(-45 - i * 32)
            if i % 2 == 1:
                self._create_item('TREASURE', -35 - i * 48)
            if i % 3 == 0:
                self._create_item('BOOST', -70 - i * 65)
    
    def _create_foe(self, z_val):
        foe = self.world.registry.create('FOE')
        lane = random.choice(LANES)
        foe.attach('transform', Transform(lane, 0.6, z_val))
        foe.attach('vitality', Health(50))
        foe.attach('motion', Motion(0, 0, random.uniform(5, 10)))
        
        r = random.uniform(0.75, 1.0)
        g = random.uniform(0.0, 0.25)
        b = random.uniform(0.0, 0.25)
        foe.attach('visuals', Visuals((r, g, b), [1.4, 0.75, 2.3]))
        foe.fire_clock = 0
        foe.target_x = random.choice(LANES)
    
    def _create_barrier(self, z_val):
        barrier = self.world.registry.create('BARRIER')
        lane = random.choice(LANES)
        barrier_shape = random.choice(['CUBE', 'PYRAMID', 'BALL'])
        barrier.attach('transform', Transform(lane, 0.5, z_val))
        barrier.attach('visuals', Visuals((0.65, 0.45, 0.25), [1.6, 1.6, 1.6]))
        barrier.shape_type = barrier_shape
    
    def _create_item(self, item_type, z_val):
        item = self.world.registry.create(item_type)
        lane = random.choice(LANES)
        y_val = 1.0 if item_type == 'TREASURE' else 1.3
        rgb = (1, 0.95, 0.2) if item_type == 'TREASURE' else (1, 0.25, 0.1)
        item.attach('transform', Transform(lane, y_val, z_val))
        item.attach('visuals', Visuals(rgb, [0.45, 0.45, 0.45]))
        item.spin = 0
    
    def godmode(self, elapsed):
        if not self.world.invincible:
            return

        hero_trans = self.world.hero.fetch('transform')
        hero_arm = self.world.hero.fetch('armament')
        hero_x, hero_z = hero_trans.x, hero_trans.z

        danger_range = 35
        lane_hazards = {0: [], 1: [], 2: []}

        for barrier in self.world.registry.filter_type('BARRIER'):
            b_trans = barrier.fetch('transform')
            if hero_z - danger_range < b_trans.z < hero_z:
                for idx, lane_x in enumerate(LANES):
                    if abs(b_trans.x - lane_x) < 1.5:
                        lane_hazards[idx].append(b_trans.z)

        for foe in self.world.registry.filter_type('FOE'):
            f_trans = foe.fetch('transform')
            if hero_z - danger_range < f_trans.z < hero_z:
                for idx, lane_x in enumerate(LANES):
                    if abs(f_trans.x - lane_x) < 1.5:
                        lane_hazards[idx].append(f_trans.z)

                if abs(f_trans.x - hero_x) < 2.0 and abs(f_trans.z - hero_z) < 30:
                    if time.time() - hero_arm.fire_time > FIRE_DELAY:
                        self._launch_shot([hero_x, hero_trans.y + 0.6, hero_z - 2.5], 'HERO')
                        hero_arm.fire_time = time.time()

        current = hero_trans.desired_lane
        best_lane = current
        min_threat = float('inf')

        for lane_idx in range(3):
            if not lane_hazards[lane_idx]:
                threat_score = 0
            else:
                threat_score = sum(1.0 / abs(hero_z - z) for z in lane_hazards[lane_idx])
            if threat_score < min_threat:
                min_threat = threat_score
                best_lane = lane_idx

        if lane_hazards[current]:
            nearest_z = min(lane_hazards[current])
            if abs(hero_z - nearest_z) < 15 and best_lane != current:
                hero_trans.desired_lane = best_lane

        for item_type in ('TREASURE', 'BOOST'):
            for item in self.world.registry.filter_type(item_type):
                i_trans = item.fetch('transform')
                if hero_z - 20 < i_trans.z < hero_z + 5:
                    for idx, lane_x in enumerate(LANES):
                        if abs(i_trans.x - lane_x) < 1.5:
                            if not lane_hazards[idx] or abs(hero_z - i_trans.z) < 8:
                                hero_trans.desired_lane = idx
                                break
    
    def tick(self, elapsed):
        self.world.stats['travel'] += self.world.stats['pace'] * elapsed
        self.world.stats['pace'] += 0.6 * elapsed

        hero_trans = self.world.hero.fetch('transform')
        hero_trans.z -= self.world.stats['pace'] * elapsed

        self.godmode(elapsed)

        target_x = LANES[hero_trans.desired_lane]
        if hero_trans.x < target_x:
            hero_trans.x = min(hero_trans.x + 22 * elapsed, target_x)
        elif hero_trans.x > target_x:
            hero_trans.x = max(hero_trans.x - 22 * elapsed, target_x)

        self._process_foes(elapsed)
        self._process_shots(elapsed)
        self._process_items(elapsed)
        self._detect_impacts()
        self._spawn_more()

        hero_vit = self.world.hero.fetch('vitality')
        if self.world.invincible:
            hero_vit.val = hero_vit.max_val

        if not hero_vit.alive:
            return 'FINISHED'

        return None
    
    def _process_foes(self, elapsed):
        hero_trans = self.world.hero.fetch('transform')
        
        for foe in self.world.registry.filter_type('FOE'):
            f_trans = foe.fetch('transform')
            f_motion = foe.fetch('motion')
            f_trans.z += f_motion.vz * elapsed
            
            if f_trans.x < foe.target_x:
                f_trans.x = min(f_trans.x + 6 * elapsed, foe.target_x)
            elif f_trans.x > foe.target_x:
                f_trans.x = max(f_trans.x - 6 * elapsed, foe.target_x)
            
            if f_trans.z > hero_trans.z + 35:
                self.world.registry.remove(foe)
                self._create_foe(hero_trans.z - 100)
                continue
            
            if abs(f_trans.z - hero_trans.z) < 25 and time.time() - foe.fire_clock > 2.2:
                dx = abs(f_trans.x - hero_trans.x)
                if dx > 3.5:
                    self._launch_shot([f_trans.x, f_trans.y, f_trans.z], 'FOE')
                    foe.fire_clock = time.time()
    
    def _process_shots(self, elapsed):
        hero_trans = self.world.hero.fetch('transform')
        
        for shot in self.world.registry.filter_type('SHOT'):
            s_trans = shot.fetch('transform')
            s_motion = shot.fetch('motion')
            
            if shot.origin == 'HERO':
                s_trans.z -= s_motion.vz * elapsed
            else:
                s_trans.z += s_motion.vz * 0.55 * elapsed
                dx = hero_trans.x - s_trans.x
                if abs(dx) > 0.6:
                    s_trans.x += (dx / abs(dx)) * 12 * elapsed
            
            if abs(s_trans.z - hero_trans.z) > 220:
                self.world.registry.remove(shot)
    
    def _process_items(self, elapsed):
        for item_type in ['TREASURE', 'BOOST']:
            for item in self.world.registry.filter_type(item_type):
                item.spin += 200 * elapsed if item_type == 'TREASURE' else 140 * elapsed
                
                i_trans = item.fetch('transform')
                hero_trans = self.world.hero.fetch('transform')
                
                if i_trans.z > hero_trans.z + 25:
                    self.world.registry.remove(item)
    
    def _detect_impacts(self):
        hero_trans = self.world.hero.fetch('transform')
        hero_vit = self.world.hero.fetch('vitality')
        hero_pos = (hero_trans.x, hero_trans.z)

        for shot in self.world.registry.filter_type('SHOT'):
            shot_trans = shot.fetch('transform')
            shot_pos = (shot_trans.x, shot_trans.z)

            if shot.origin == 'HERO':
                for foe in self.world.registry.filter_type('FOE'):
                    f_trans = foe.fetch('transform')
                    foe_pos = (f_trans.x, f_trans.z)
                    if self._near(shot_pos, foe_pos, 2.2):
                        f_vit = foe.fetch('vitality')
                        if not f_vit.damage(50):
                            self.world.stats['points'] += 110
                            self.world.stats['defeats'] += 1
                            self._make_fragments([f_trans.x, f_trans.y, f_trans.z])
                            self.world.registry.remove(foe)
                            self._create_foe(hero_pos[1] - 100)

                        self.world.registry.remove(shot)
                        break
            else:
                if self._near(shot_pos, hero_pos, 1.8):
                    if not self.world.invincible:
                        hero_vit.damage(12)
                    self.world.registry.remove(shot)

        for item_type in ['TREASURE', 'BOOST']:
            for item in self.world.registry.filter_type(item_type):
                i_trans = item.fetch('transform')
                item_pos = (i_trans.x, i_trans.z)
                if self._near(item_pos, hero_pos, 1.7):
                    if item_type == 'TREASURE':
                        self.world.stats['points'] += 55
                    else:
                        destroyed = 0
                        for foe in self.world.registry.filter_type('FOE'):
                            f_trans = foe.fetch('transform')
                            if abs(f_trans.z - i_trans.z) < 55:
                                self.world.stats['points'] += 110
                                self.world.stats['defeats'] += 1
                                destroyed += 1
                                self._make_fragments([f_trans.x, f_trans.y, f_trans.z])
                                self.world.registry.remove(foe)
                                self._create_foe(hero_pos[1] - 100)

                    self.world.registry.remove(item)

        for barrier in self.world.registry.filter_type('BARRIER'):
            b_trans = barrier.fetch('transform')
            barrier_pos = (b_trans.x, b_trans.z)
            if self._near(barrier_pos, hero_pos, 1.7):
                if not self.world.invincible:
                    hero_vit.damage(18)
                self.world.registry.remove(barrier)

    def _near(self, pos1, pos2, limit):
        dx = pos1[0] - pos2[0]
        dz = pos1[1] - pos2[1]
        return math.sqrt(dx*dx + dz*dz) < limit
    
    def _launch_shot(self, coords, origin):
        shot = self.world.registry.create('SHOT')
        shot.attach('transform', Transform(coords[0], coords[1], coords[2]))
        velocity = 110 if origin == 'HERO' else 65
        shot.attach('motion', Motion(0, 0, velocity))
        rgb = (1, 1, 0.2) if origin == 'HERO' else (1, 0.4, 0.1)
        shot.attach('visuals', Visuals(rgb, [0.25, 0.25, 0.25]))
        shot.origin = origin
    
    def _make_fragments(self, coords):
        for k in range(9):
            frag = self.world.registry.create('FRAGMENT')
            frag.attach('transform', Transform(coords[0], coords[1], coords[2]))
            vx = random.uniform(-6, 6)
            vy = random.uniform(3, 9)
            vz = random.uniform(-6, 6)
            frag.attach('motion', Motion(vx, vy, vz))
            frag.attach('visuals', Visuals((0.85, 0.25, 0.25), [0.35, 0.35, 0.35]))
            frag.timer = 0.6
        
        for frag in self.world.registry.filter_type('FRAGMENT')[:]:
            f_trans = frag.fetch('transform')
            f_motion = frag.fetch('motion')
            
            frag.timer -= 0.016
            if frag.timer <= 0:
                self.world.registry.remove(frag)
                continue
            
            f_trans.x += f_motion.vx * 0.016
            f_trans.y += f_motion.vy * 0.016
            f_trans.z += f_motion.vz * 0.016
            f_motion.vy -= 22 * 0.016
    
    def _spawn_more(self):
        hero_trans = self.world.hero.fetch('transform')
        spawn_z = hero_trans.z - 60
        
        foe_count = len(self.world.registry.filter_type('FOE'))
        if foe_count == 0:
            self._create_foe(spawn_z)
        
        if random.random() < 0.025:
            self._create_barrier(spawn_z - random.randint(0, 45))
        
        if random.random() < 0.018:
            self._create_item('TREASURE', spawn_z - random.randint(0, 35))
        
        if random.random() < 0.01:
            self._create_item('BOOST', spawn_z - random.randint(0, 65))
    
    def paint(self):
        self._configure_view()
        self._paint_world()
        self._paint_objects()
        self._paint_overlay()
    
    def _configure_view(self):
        glLoadIdentity()
        hero_trans = self.world.hero.fetch('transform')
        
        if self.world.view_mode == 'FIRST':
            gluLookAt(hero_trans.x, hero_trans.y + 1.3, hero_trans.z, 
                     hero_trans.x, hero_trans.y + 1.3, hero_trans.z - 110, 
                     0, 1, 0)
        else:
            gluLookAt(hero_trans.x, 7.5, hero_trans.z + 18, 
                     hero_trans.x, 1, hero_trans.z - 8, 
                     0, 1, 0)
    
    def _paint_world(self):
        hero_trans = self.world.hero.fetch('transform')
        
        glColor3f(0.35, 0.35, 0.35)
        glBegin(GL_QUADS)
        glVertex3f(-ROAD_W/2, 0, hero_trans.z + 110)
        glVertex3f(ROAD_W/2, 0, hero_trans.z + 110)
        glVertex3f(ROAD_W/2, 0, hero_trans.z - 550)
        glVertex3f(-ROAD_W/2, 0, hero_trans.z - 550)
        glEnd()
        
        glColor3f(1, 0.95, 0.2)
        z = int(hero_trans.z - 550)
        end = int(hero_trans.z + 110)
        while z < end:
            for lx in [LANES[0], LANES[2]]:
                glBegin(GL_QUADS)
                glVertex3f(lx - 0.12, 0.02, z)
                glVertex3f(lx + 0.12, 0.02, z)
                glVertex3f(lx + 0.12, 0.02, z - 3.5)
                glVertex3f(lx - 0.12, 0.02, z - 3.5)
                glEnd()
            z += 6
        
        glColor3f(0.25, 0.65, 0.25)
        glBegin(GL_QUADS)
        glVertex3f(-GRASS_LIMIT, 0, hero_trans.z + 110)
        glVertex3f(-ROAD_W/2, 0, hero_trans.z + 110)
        glVertex3f(-ROAD_W/2, 0, hero_trans.z - 550)
        glVertex3f(-GRASS_LIMIT, 0, hero_trans.z - 550)
        glEnd()
        glBegin(GL_QUADS)
        glVertex3f(ROAD_W/2, 0, hero_trans.z + 110)
        glVertex3f(GRASS_LIMIT, 0, hero_trans.z + 110)
        glVertex3f(GRASS_LIMIT, 0, hero_trans.z - 550)
        glVertex3f(ROAD_W/2, 0, hero_trans.z - 550)
        glEnd()
        
        start = int(hero_trans.z / -16) - 12
        for side in [-38, 38]:
            for i in range(start, start + 55):
                mz = i * -16
                h = 20 + (hash(f"{side}{i}") % 14)
                r = 8 + (hash(f"r{side}{i}") % 5)
                snow = h * 0.7
                
                glPushMatrix()
                glTranslatef(side, 0, mz)
                glColor3f(0.45, 0.38, 0.32)
                glRotatef(-90, 1, 0, 0)
                q = gluNewQuadric()
                gluCylinder(q, r, r * 0.35, snow, 16, 16)
                glPopMatrix()
                
                glPushMatrix()
                glTranslatef(side, snow, mz)
                glColor3f(0.98, 0.98, 0.98)
                glRotatef(-90, 1, 0, 0)
                q = gluNewQuadric()
                gluCylinder(q, r * 0.35, 0, h - snow, 16, 16)
                glPopMatrix()
    
    def _paint_objects(self):
        self._paint_hero()
        
        for foe in self.world.registry.filter_type('FOE'):
            self._paint_foe(foe)
        
        for shot in self.world.registry.filter_type('SHOT'):
            self._paint_shot(shot)
        
        for barrier in self.world.registry.filter_type('BARRIER'):
            self._paint_barrier(barrier)
        
        for item_type in ['TREASURE', 'BOOST']:
            for item in self.world.registry.filter_type(item_type):
                self._paint_item(item, item_type)
        
        for frag in self.world.registry.filter_type('FRAGMENT'):
            self._paint_fragment(frag)
    
    def _paint_hero(self):
        trans = self.world.hero.fetch('transform')
        vis = self.world.hero.fetch('visuals')
        
        if self.world.view_mode == 'FIRST':
            glPushMatrix()
            glTranslatef(trans.x, trans.y, trans.z)
            glColor3f(*vis.rgb)
            glPushMatrix()
            glTranslatef(0, 0.85, -1.6)
            glScalef(1.1, 0.25, 0.9)
            self._render_box(1)
            glPopMatrix()
            glPopMatrix()
            return
        
        glPushMatrix()
        glTranslatef(trans.x, trans.y, trans.z)
        glColor3f(*vis.rgb)
        glPushMatrix()
        glScalef(*vis.dimensions)
        self._render_box(1)
        glPopMatrix()
        
        glColor3f(0.35, 0.65, 1.05)
        glPushMatrix()
        glTranslatef(0, 0.55, -0.35)
        glScalef(0.95, 0.55, 1.05)
        self._render_box(1)
        glPopMatrix()
        
        glColor3f(0.15, 0.15, 0.15)
        for wx, wz in [(-0.65, -0.85), (0.65, -0.85), (-0.65, 0.85), (0.65, 0.85)]:
            glPushMatrix()
            glTranslatef(wx, -0.25, wz)
            q = gluNewQuadric()
            gluSphere(q, 0.35, 12, 12)
            glPopMatrix()
        glPopMatrix()
    
    def _paint_foe(self, foe):
        trans = foe.fetch('transform')
        vis = foe.fetch('visuals')
        
        glPushMatrix()
        glTranslatef(trans.x, trans.y, trans.z)
        glColor3f(*vis.rgb)
        glPushMatrix()
        glScalef(*vis.dimensions)
        self._render_box(1)
        glPopMatrix()
        
        shade = tuple(c * 0.6 for c in vis.rgb)
        glColor3f(*shade)
        glPushMatrix()
        glTranslatef(0, 0.55, -0.25)
        glScalef(1.05, 0.55, 1.25)
        self._render_box(1)
        glPopMatrix()
        
        glColor3f(0.12, 0.12, 0.12)
        for wx, wz in [(-0.75, -0.95), (0.75, -0.95), (-0.75, 0.95), (0.75, 0.95)]:
            glPushMatrix()
            glTranslatef(wx, -0.25, wz)
            q = gluNewQuadric()
            gluSphere(q, 0.4, 12, 12)
            glPopMatrix()
        glPopMatrix()
    
    def _paint_shot(self, shot):
        trans = shot.fetch('transform')
        vis = shot.fetch('visuals')
        
        glPushMatrix()
        glTranslatef(trans.x, trans.y, trans.z)
        glColor3f(*vis.rgb)
        q = gluNewQuadric()
        gluSphere(q, 0.25, 10, 10)
        glPopMatrix()
    
    def _paint_barrier(self, barrier):
        trans = barrier.fetch('transform')
        vis = barrier.fetch('visuals')
        
        glPushMatrix()
        glTranslatef(trans.x, trans.y, trans.z)
        
        if barrier.shape_type == 'CUBE':
            glColor3f(*vis.rgb)
            self._render_box(1.6)
        elif barrier.shape_type == 'PYRAMID':
            glColor3f(1, 0.6, 0.1)
            glRotatef(-90, 1, 0, 0)
            q = gluNewQuadric()
            gluCylinder(q, 0.55, 0, 1.6, 12, 12)
        elif barrier.shape_type == 'BALL':
            glColor3f(0.35, 0.35, 0.35)
            q = gluNewQuadric()
            gluSphere(q, 0.55, 12, 12)
        
        glPopMatrix()
    
    def _paint_item(self, item, item_type):
        trans = item.fetch('transform')
        vis = item.fetch('visuals')
        
        glPushMatrix()
        glTranslatef(trans.x, trans.y, trans.z)
        glRotatef(item.spin, 0, 1, 0)
        glColor3f(*vis.rgb)
        
        if item_type == 'TREASURE':
            q = gluNewQuadric()
            gluSphere(q, 0.45, 14, 14)
        else:
            self._render_box(1.3)
            glColor3f(1, 0.95, 0.2)
            glScalef(0.65, 0.65, 0.65)
            self._render_box(1)
        
        glPopMatrix()
    
    def _paint_fragment(self, frag):
        trans = frag.fetch('transform')
        vis = frag.fetch('visuals')
        
        glPushMatrix()
        glTranslatef(trans.x, trans.y, trans.z)
        glColor3f(*vis.rgb)
        self._render_box(0.35)
        glPopMatrix()
    
    def _render_box(self, scale):
        h = scale / 2
        glBegin(GL_QUADS)
        glVertex3f(-h, -h, h); glVertex3f(h, -h, h); glVertex3f(h, h, h); glVertex3f(-h, h, h)
        glVertex3f(-h, -h, -h); glVertex3f(-h, h, -h); glVertex3f(h, h, -h); glVertex3f(h, -h, -h)
        glVertex3f(-h, h, -h); glVertex3f(-h, h, h); glVertex3f(h, h, h); glVertex3f(h, h, -h)
        glVertex3f(-h, -h, -h); glVertex3f(h, -h, -h); glVertex3f(h, -h, h); glVertex3f(-h, -h, h)
        glVertex3f(h, -h, -h); glVertex3f(h, h, -h); glVertex3f(h, h, h); glVertex3f(h, -h, h)
        glVertex3f(-h, -h, -h); glVertex3f(-h, -h, h); glVertex3f(-h, h, h); glVertex3f(-h, h, -h)
        glEnd()
    
    def _paint_overlay(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, WIN_W, 0, WIN_H)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glColor3f(0.95, 0.95, 0.95)
        
        hero_vit = self.world.hero.fetch('vitality')
        
        self._display_info(15, WIN_H - 35, f"HP: {int(hero_vit.val)}")
        self._display_info(15, WIN_H - 65, f"SCORE: {int(self.world.stats['points'])}")
        self._display_info(15, WIN_H - 95, f"DIST: {int(self.world.stats['travel'])} meters")
        self._display_info(15, WIN_H - 125, f"SPEED: {int(self.world.stats['pace'])} km/h")
        self._display_info(15, WIN_H - 155, f"KILLS: {self.world.stats['defeats']}")
        
        view_label = "FIRST PERSON" if self.world.view_mode == 'FIRST' else "THIRD PERSON"
        self._display_info(15, WIN_H - 185, f"CAM: {view_label}")
        
        if self.world.invincible:
            glColor3f(1, 0.2, 0.2)
            self._display_info(15, WIN_H - 215, "GOD MODE ACTIVE")
            glColor3f(0.95, 0.95, 0.95)
        
        self._display_info(15, 55, "Arrow Keys: Lane | I/RMB: Fire | K/LMB: Bomb | V: Camera | G: God Mode")
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
    
    def _display_info(self, x, y, msg):
        glRasterPos2f(x, y)
        for c in msg:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))

class Finished(Phase):
    def paint(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, WIN_W, 0, WIN_H)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glColor3f(1, 0.2, 0.2)
        self._display_info(WIN_W//2 - 85, WIN_H//2 + 55, "WRECKED")
        
        glColor3f(0.95, 0.95, 0.95)
        self._display_info(WIN_W//2 - 105, WIN_H//2, 
                         f"Final Score: {int(self.world.stats['points'])}")
        self._display_info(WIN_W//2 - 125, WIN_H//2 - 35, 
                         f"Enemies Destroyed: {self.world.stats['defeats']}")
        self._display_info(WIN_W//2 - 125, WIN_H//2 - 75, 
                         "Press Q to restart menu")
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
    
    def _display_info(self, x, y, msg):
        glRasterPos2f(x, y)
        for c in msg:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
    
    def process_key(self, key):
        if key in (b'q', b'Q'):
            return 'MENU'
        return None

class World:
    def __init__(self):
        self.phases = {
            'MENU': Menu(self),
            'RUNNING': Running(self),
            'FINISHED': Finished(self)
        }
        self.active_phase_name = 'MENU'
        self.active_phase = self.phases['MENU']
        self.active_phase.on_enter()
        
        self.key_states = {}
        self.mouse_states = {}
        self.timer = time.time()
        
        self.view_mode = 'THIRD'
        self.invincible = False
        
        self.stats = {
            'points': 0,
            'pace': 22.0,
            'travel': 0.0,
            'defeats': 0
        }
        
        self.registry = Objectreg()
        self.hero = None
    
    def switch_phase(self, phase_name):
        if phase_name in self.phases:
            self.active_phase.on_exit()
            self.active_phase_name = phase_name
            self.active_phase = self.phases[phase_name]
            self.active_phase.on_enter()
    
    def update_world(self):
        current = time.time()
        elapsed = min(0.055, current - self.timer)
        self.timer = current
        
        next_phase = self.active_phase.tick(elapsed)
        if next_phase:
            self.switch_phase(next_phase)
    
    def draw_world(self):
        self.active_phase.paint()
    
    def key_down(self, key):
        self.key_states[key] = True
        
        if self.active_phase_name == 'MENU':
            next_phase = self.active_phase.process_key(key)
            if next_phase:
                mode = self.active_phase.mode_choice
                speed_values = {"Easy": 17, "Normal": 22, "Hard": 50}
                self.stats['pace'] = speed_values[mode]
                self.stats['points'] = 0
                self.stats['travel'] = 0
                self.stats['defeats'] = 0
                self.switch_phase(next_phase)
        
        elif self.active_phase_name == 'RUNNING':
            if key in (b'g', b'G'):
                self.invincible = not self.invincible
                status = "ENABLED" if self.invincible else "DISABLED"
                print(f"[GOD MODE] {status}")
            elif key in (b'v', b'V'):
                self.view_mode = 'FIRST' if self.view_mode == 'THIRD' else 'THIRD'

            elif key in (b'i', b'I'):
                arm = self.hero.fetch('armament')
                if time.time() - arm.fire_time > FIRE_DELAY:
                    trans = self.hero.fetch('transform')
                    self.active_phase._launch_shot([trans.x, trans.y + 0.6, trans.z - 2.5], 'HERO')
                    arm.fire_time = time.time()
        
        elif self.active_phase_name == 'FINISHED':
            next_phase = self.active_phase.process_key(key)
            if next_phase:
                self.switch_phase(next_phase)
    
    def key_up(self, key):
        self.key_states[key] = False

    def special_key_down(self, key):
        if self.active_phase_name == 'RUNNING':
            if key == GLUT_KEY_LEFT:
                trans = self.hero.fetch('transform')
                if trans.desired_lane > 0:
                    trans.desired_lane -= 1
            elif key == GLUT_KEY_RIGHT:
                trans = self.hero.fetch('transform')
                if trans.desired_lane < 2:
                    trans.desired_lane += 1

    def mouse_action(self, btn, action, x, y):
        if self.active_phase_name == 'RUNNING':
            if btn == 0 and action == 0:
                arm = self.hero.fetch('armament')
                if time.time() - arm.bomb_time > BOMB_DELAY:
                    trans = self.hero.fetch('transform')
                    self.active_phase._launch_shot([trans.x - 0.65, trans.y, trans.z + 2.5], 'HERO')
                    self.active_phase._launch_shot([trans.x + 0.65, trans.y, trans.z + 2.5], 'HERO')
                    arm.bomb_time = time.time()
            elif btn == 2 and action == 0:
                arm = self.hero.fetch('armament')
                if time.time() - arm.fire_time > FIRE_DELAY:
                    trans = self.hero.fetch('transform')
                    self.active_phase._launch_shot([trans.x, trans.y + 0.6, trans.z - 2.5], 'HERO')
                    arm.fire_time = time.time()

world = None

def display_handler():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    world.draw_world()
    glutSwapBuffers()

def keyboard_handler(key, x, y):
    world.key_down(key)
    glutPostRedisplay()

def keyboard_release_handler(key, x, y):
    world.key_up(key)

def special_key_handler(key, x, y):
    world.special_key_down(key)
    glutPostRedisplay()

def mouse_handler(btn, action, x, y):
    world.mouse_action(btn, action, x, y)
    glutPostRedisplay()

def idle():
    world.update_world()
    glutPostRedisplay()

def setup():
    glClearColor(0.56, 0, 1, 1)
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(65, WIN_W / WIN_H, 0.1, 520.0)
    glMatrixMode(GL_MODELVIEW)

def main():
    global world
    world = World()
    
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"DHAKA DASH")
    
    setup()
    glutDisplayFunc(display_handler)
    glutKeyboardFunc(keyboard_handler)
    glutKeyboardUpFunc(keyboard_release_handler)
    glutSpecialFunc(special_key_handler)
    glutMouseFunc(mouse_handler)
    glutIdleFunc(idle)
    glutMainLoop()

if __name__ == "__main__":
    main()