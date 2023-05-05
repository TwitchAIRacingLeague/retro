import gc
import gym
import gzip
import gym.spaces
import json
import numpy as np
import os
import retro
import retro.data
from gym.utils import seeding
import hashlib
import struct
from typing import Optional 

# TODO: don't hardcode sizeof_int here
def _bigint_from_bytes(bt: bytes) -> int:
    
    sizeof_int = 4
    padding = sizeof_int - len(bt) % sizeof_int
    bt += b"\0" * padding
    int_count = int(len(bt) / sizeof_int)
    unpacked = struct.unpack(f"{int_count}I", bt)
    accum = 0
    for i, val in enumerate(unpacked):
        accum += 2 ** (sizeof_int * 8 * i) * val
    return accum

def hash_seed(seed: Optional[int] = None, max_bytes: int = 8) -> int:
    """Any given evaluation is likely to have many PRNG's active at once.
    (Most commonly, because the environment is running in multiple processes.)
    There's literature indicating that having linear correlations between seeds of multiple PRNG's can correlate the outputs:
        http://blogs.unity3d.com/2015/01/07/a-primer-on-repeatable-random-numbers/
        http://stackoverflow.com/questions/1554958/how-different-do-random-seeds-need-to-be
        http://dl.acm.org/citation.cfm?id=1276928
    Thus, for sanity we hash the seeds before using them. (This scheme is likely not crypto-strength, but it should be good enough to get rid of simple correlations.)
    Args:
        seed: None seeds from an operating system specific randomness source.
        max_bytes: Maximum number of bytes to use in the hashed seed.
    Returns:
        The hashed seed
    """

    if seed is None:
        seed = create_seed(max_bytes=max_bytes)
    hash = hashlib.sha512(str(seed).encode("utf8")).digest()
    return _bigint_from_bytes(hash[:max_bytes])

gym.utils.seeding.hash_seed = hash_seed

try:
    import pyglet
except ImportError as e:
    raise ImportError(
        """
    Cannot import pyglet.
    HINT: you can install pyglet directly via 'pip install pyglet'.
    But if you really just want to install all Gym dependencies and not have to think about it,
    'pip install -e .[all]' or 'pip install gym[all]' will do it.
    """
    )

try:
    from pyglet.gl import *
except ImportError as e:
    raise ImportError(
        """
    Error occurred while running `from pyglet.gl import *`
    HINT: make sure you have OpenGL installed. On Ubuntu, you can run 'apt-get install python-opengl'.
    If you're running on a server, you may need a virtual frame buffer; something like this should work:
    'xvfb-run -s \"-screen 0 1400x900x24\" python <your_script.py>'
    """
    )
from gym.utils import seeding

gym_version = tuple(int(x) for x in gym.__version__.split('.'))

__all__ = ['RetroEnv']


def get_window(width, height, display, **kwargs):
    """
    Will create a pyglet window from the display specification provided.
    """
    screen = display.get_screens()  # available screens
    config = screen[0].get_best_config()  # selecting the first screen
    context = config.create_context(None)  # create GL context

    return pyglet.window.Window(
        width=width,
        height=height,
        display=display,
        config=config,
        context=context,
        **kwargs
    )

def get_display(spec):
    """Convert a display specification (such as :0) into an actual Display
    object.
    Pyglet only supports multiple Displays on Linux.
    """
    if spec is None:
        return pyglet.canvas.get_display()
        # returns already available pyglet_display,
        # if there is no pyglet display available then it creates one
    elif isinstance(spec, str):
        return pyglet.canvas.Display(spec)
    else:
        raise error.Error(
            "Invalid display specification: {}. (Must be a string like :0 or None.)".format(
                spec
            )
        )

class SimpleImageViewer(object):
    def __init__(self, display=None, maxwidth=500):
        self.window = None
        self.isopen = False
        self.display = get_display(display)
        self.maxwidth = maxwidth

    def imshow(self, arr):
        if self.window is None:
            height, width, _channels = arr.shape
            if width > self.maxwidth:
                scale = self.maxwidth / width
                width = int(scale * width)
                height = int(scale * height)
            self.window = get_window(
                width=width,
                height=height,
                display=self.display,
                vsync=False,
                resizable=True,
            )
            self.width = width
            self.height = height
            self.isopen = True

            @self.window.event
            def on_resize(width, height):
                self.width = width
                self.height = height

            @self.window.event
            def on_close():
                self.isopen = False

        assert len(arr.shape) == 3, "You passed in an image with the wrong number shape"
        image = pyglet.image.ImageData(
            arr.shape[1], arr.shape[0], "RGB", arr.tobytes(), pitch=arr.shape[1] * -3
        )
        texture = image.get_texture()
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        texture.width = self.width
        texture.height = self.height
        self.window.clear()
        self.window.switch_to()
        self.window.dispatch_events()
        texture.blit(0, 0)  # draw
        self.window.flip()
gym_version = tuple(int(x) for x in gym.__version__.split('.'))

__all__ = ['RetroEnv']


class RetroEnv(gym.Env):
    """
    Gym Retro environment class

    Provides a Gym interface to classic video games
    """
    metadata = {'render.modes': ['human', 'rgb_array'],
                'video.frames_per_second': 60.0}

    def __init__(self, game, state=retro.State.DEFAULT, scenario=None, info=None, use_restricted_actions=retro.Actions.FILTERED,
                 record=False, players=1, inttype=retro.data.Integrations.STABLE, obs_type=retro.Observations.IMAGE):
        if not hasattr(self, 'spec'):
            self.spec = None
        self._obs_type = obs_type
        self.img = None
        self.ram = None
        self.viewer = None
        self.gamename = game
        self.statename = state
        self.initial_state = None
        self.players = players

        metadata = {}
        rom_path = retro.data.get_romfile_path(game, inttype)
        metadata_path = retro.data.get_file_path(game, 'metadata.json', inttype)

        if state == retro.State.NONE:
            self.statename = None
        elif state == retro.State.DEFAULT:
            self.statename = None
            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                if 'default_player_state' in metadata and self.players <= len(metadata['default_player_state']):
                    self.statename = metadata['default_player_state'][self.players - 1]
                elif 'default_state' in metadata:
                    self.statename = metadata['default_state']
                else:
                    self.statename = None
            except (IOError, json.JSONDecodeError):
                pass

        if self.statename:
            self.load_state(self.statename, inttype)        if info is None:
            info = 'data'

        if info.endswith('.json'):
            # assume it's a path
            info_path = info
        else:
            info_path = retro.data.get_file_path(game, info + '.json', inttype)

        if scenario is None:
            scenario = 'scenario'

        if scenario.endswith('.json'):
            # assume it's a path
            scenario_path = scenario
        else:
            scenario_path = retro.data.get_file_path(game, scenario + '.json', 

        self.data = retro.data.GameData()

        if info is None:
            info = 'data'

        if info.endswith('.json'):
            # assume it's a path
            info_path = info
        else:
            info_path = retro.data.get_file_path(game, info + '.json', inttype)

        if scenario is None:
            scenario = 'scenario'

        if scenario.endswith('.json'):
            # assume it's a path
            scenario_path = scenario
        else:
            scenario_path = retro.data.get_file_path(game, scenario + '.json', inttype)

        self.system = retro.get_romfile_system(rom_path)

        # We can't have more than one emulator per process. Before creating an
        # emulator, ensure that unused ones are garbage-collected
        gc.collect()
        self.em = retro.RetroEmulator(rom_path)
        self.em.configure_data(self.data)
        self.em.step()

        core = retro.get_system_info(self.system)
        self.buttons = core['buttons']
        self.num_buttons = len(self.buttons)

        try:
            assert self.data.load(info_path, scenario_path), 'Failed to load info (%s) or scenario (%s)' % (info_path, scenario_path)
        except Exception:
            del self.em
            raise

        self.button_combos = self.data.valid_actions()
        if use_restricted_actions == retro.Actions.DISCRETE:
            combos = 1
            for combo in self.button_combos:
                combos *= len(combo)
            self.action_space = gym.spaces.Discrete(combos ** players)
        elif use_restricted_actions == retro.Actions.MULTI_DISCRETE:
            self.action_space = gym.spaces.MultiDiscrete([len(combos) if gym_version >= (0, 9, 6) else (0, len(combos) - 1) for combos in self.button_combos] * players)
        else:
            self.action_space = gym.spaces.MultiBinary(self.num_buttons * players)

        kwargs = {}
        if gym_version >= (0, 9, 6):
            kwargs['dtype'] = np.uint8
        
        if self._obs_type == retro.Observations.RAM:
            shape = self.get_ram().shape
        else:
            img = [self.get_screen(p) for p in range(players)]
            shape = img[0].shape
        self.observation_space = gym.spaces.Box(low=0, high=255, shape=shape, **kwargs)

        self.use_restricted_actions = use_restricted_actions
        self.movie = None
        self.movie_id = 0
        self.movie_path = None
        if record is True:
            self.auto_record()
        elif record is not False:
            self.auto_record(record)
        self.seed()
        if gym_version < (0, 9, 6):
            self._seed = self.seed
            self._step = self.step
            self._reset = self.reset
            self._render = self.render
            self._close = self.close


    def loadRom(env, game):
        # This successfully loads a rom, however it doesn't jump to the "start" state as defined in the json file.
        metadata = {}
        rom = retro.data.get_romfile_path(game, retro.data.Integrations.STABLE)
        metadata_path = retro.data.get_file_path(game, 'metadata.json', retro.data.Integrations.STABLE)

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
            if 'default_player_state' in metadata and env.players <= len(metadata['default_player_state']):
                env.statename = metadata['default_player_state'][env.players - 1]
            elif 'default_state' in metadata:
                env.statename = metadata['default_state']
            else:
                env.statename = None
        except (IOError, json.JSONDecodeError):
            pass

        # The ordering could be totally wonky, I have no idea if this is right
        # Force re-loading the data and scenario .json files, also assume that the info file is "data" and scenario is scenario
        info = "data"
        info_path = retro.data.get_file_path(game, info + '.json', inttype)
        scenario = 'scenario'
        scenario_path = retro.data.get_file_path(game, scenario + '.json', inttype)

        try:
            assert self.data.load(info_path, scenario_path), 'Failed to load info (%s) or scenario (%s)' % (info_path, scenario_path)
        except Exception:
            del self.em
            raise

        env.gamename = game
        if env.statename:
            env.load_state(env.statename, retro.data.Integrations.STABLE)

        env.em.loadRom(rom)

        #env.em.configure_data(env.data)
        #env.em.step()

        env.reset()
        obs, rew, done, info = env.step([0,0,0,0,0,0,0,0,0,0,0,0])
        return obs, rew, done, info


    def _update_obs(self):
        if self._obs_type == retro.Observations.RAM:
            self.ram = self.get_ram()
            return self.ram
        elif self._obs_type == retro.Observations.IMAGE:
            self.img = self.get_screen()
            return self.img
        else:
            raise ValueError('Unrecognized observation type: {}'.format(self._obs_type))

    def action_to_array(self, a):
        actions = []
        for p in range(self.players):
            action = 0
            if self.use_restricted_actions == retro.Actions.DISCRETE:
                for combo in self.button_combos:
                    current = a % len(combo)
                    a //= len(combo)
                    action |= combo[current]
            elif self.use_restricted_actions == retro.Actions.MULTI_DISCRETE:
                ap = a[self.num_buttons * p:self.num_buttons * (p + 1)]
                for i in range(len(ap)):
                    buttons = self.button_combos[i]
                    action |= buttons[ap[i]]
            else:
                ap = a[self.num_buttons * p:self.num_buttons * (p + 1)]
                for i in range(len(ap)):
                    action |= int(ap[i]) << i
                if self.use_restricted_actions == retro.Actions.FILTERED:
                    action = self.data.filter_action(action)
            ap = np.zeros([self.num_buttons], np.uint8)
            for i in range(self.num_buttons):
                ap[i] = (action >> i) & 1
            actions.append(ap)
        return actions

    def step(self, a):
        if self.img is None and self.ram is None:
            raise RuntimeError('Please call env.reset() before env.step()')

        for p, ap in enumerate(self.action_to_array(a)):
            if self.movie:
                for i in range(self.num_buttons):
                    self.movie.set_key(i, ap[i], p)
            self.em.set_button_mask(ap, p)

        if self.movie:
            self.movie.step()
        self.em.step()
        self.data.update_ram()
        ob = self._update_obs()
        rew, done, info = self.compute_step()
        return ob, rew, bool(done), dict(info)

    def reset(self):
        if self.initial_state:
            self.em.set_state(self.initial_state)
        for p in range(self.players):
            self.em.set_button_mask(np.zeros([self.num_buttons], np.uint8), p)
        self.em.step()
        if self.movie_path is not None:
            rel_statename = os.path.splitext(os.path.basename(self.statename))[0]
            self.record_movie(os.path.join(self.movie_path, '%s-%s-%06d.bk2' % (self.gamename, rel_statename, self.movie_id)))
            self.movie_id += 1
        if self.movie:
            self.movie.step()
        self.data.reset()
        self.data.update_ram()
        return self._update_obs()

    def seed(self, seed=None):
        self.np_random, seed1 = seeding.np_random(seed)
        # Derive a random seed. This gets passed as a uint, but gets
        # checked as an int elsewhere, so we need to keep it below
        # 2**31.
        seed2 = seeding.hash_seed(seed1 + 1) % 2**31
        return [seed1, seed2]

    def render(self, mode='human', close=False):
        if close:
            if self.viewer:
                self.viewer.close()
            return

        img = self.get_screen() if self.img is None else self.img
        if mode == "rgb_array":
            return img
        elif mode == "human":
            if self.viewer is None:
                # This can be removed as we moved SimpleImageViewer into this file as a workaround.
                #from gym.envs.classic_control.rendering import SimpleImageViewer
                self.viewer = SimpleImageViewer()
            self.viewer.imshow(img)
            return self.viewer.isopen

    def close(self):
        if hasattr(self, 'em'):
            del self.em

    def get_action_meaning(self, act):
        actions = []
        for p, action in enumerate(self.action_to_array(act)):
            actions.append([self.buttons[i] for i in np.extract(action, np.arange(len(action)))])
        if self.players == 1:
            return actions[0]
        return actions

    def get_ram(self):
        blocks = []
        for offset in sorted(self.data.memory.blocks):
            arr = np.frombuffer(self.data.memory.blocks[offset], dtype=np.uint8)
            blocks.append(arr)
        return np.concatenate(blocks)

    def get_screen(self, player=0):
        img = self.em.get_screen()
        x, y, w, h = self.data.crop_info(player)
        if not w or x + w > img.shape[1]:
            w = img.shape[1]
        else:
            w += x
        if not h or y + h > img.shape[0]:
            h = img.shape[0]
        else:
            h += y
        if x == 0 and y == 0 and w == img.shape[1] and h == img.shape[0]:
            return img
        return img[y:h, x:w]

    def load_state(self, statename, inttype=retro.data.Integrations.DEFAULT):
        if not statename.endswith('.state'):
                statename += '.state'

        with gzip.open(retro.data.get_file_path(self.gamename, statename, inttype), 'rb') as fh:
            self.initial_state = fh.read()

        self.statename = statename

    def compute_step(self):
        if self.players > 1:
            reward = [self.data.current_reward(p) for p in range(self.players)]
        else:
            reward = self.data.current_reward()
        done = self.data.is_done()
        return reward, done, self.data.lookup_all()

    def record_movie(self, path):
        self.movie = retro.Movie(path, True, self.players)
        self.movie.configure(self.gamename, self.em)
        if self.initial_state:
            self.movie.set_state(self.initial_state)

    def stop_record(self):
        self.movie_path = None
        self.movie_id = 0
        if self.movie:
            self.movie.close()
            self.movie = None

    def auto_record(self, path=None):
        if not path:
            path = os.getcwd()
        self.movie_path = path
