// Minimal, synchronous libretro host. Sonic-specific semantics stay outside it.
#include <libretro.h>

#include <array>
#include <atomic>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <dlfcn.h>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <map>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

// EGL is loaded dynamically: this host does not require EGL development headers.
using EGLBoolean = unsigned int;
using EGLenum = unsigned int;
using EGLint = int;
using EGLDisplay = void*;
using EGLConfig = void*;
using EGLSurface = void*;
using EGLContext = void*;
constexpr EGLBoolean EGL_FALSE_VALUE = 0;
constexpr EGLint EGL_NONE_VALUE = 0x3038;
constexpr EGLint EGL_SURFACE_TYPE_VALUE = 0x3033;
constexpr EGLint EGL_PBUFFER_BIT_VALUE = 0x0001;
constexpr EGLint EGL_RENDERABLE_TYPE_VALUE = 0x3040;
constexpr EGLint EGL_OPENGL_BIT_VALUE = 0x0008;
constexpr EGLint EGL_RED_SIZE_VALUE = 0x3024;
constexpr EGLint EGL_GREEN_SIZE_VALUE = 0x3023;
constexpr EGLint EGL_BLUE_SIZE_VALUE = 0x3022;
constexpr EGLint EGL_ALPHA_SIZE_VALUE = 0x3021;
constexpr EGLint EGL_PBUFFER_WIDTH_VALUE = 0x3057;
constexpr EGLint EGL_PBUFFER_HEIGHT_VALUE = 0x3056;
constexpr EGLenum EGL_OPENGL_API_VALUE = 0x30A2;
constexpr EGLenum EGL_PLATFORM_SURFACELESS_MESA_VALUE = 0x31DD;
constexpr EGLint EGL_CONTEXT_MAJOR_VERSION_KHR_VALUE = 0x3098;
constexpr EGLint EGL_CONTEXT_MINOR_VERSION_KHR_VALUE = 0x30FB;
constexpr EGLint EGL_CONTEXT_OPENGL_PROFILE_MASK_KHR_VALUE = 0x30FD;
constexpr EGLint EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT_KHR_VALUE = 0x00000001;

std::string DynamicLoaderError()
{
  const char* error = dlerror();
  return error ? error : "unknown dynamic loader error";
}

class EglContext {
public:
  EglContext() = default;
  EglContext(const EglContext&) = delete;
  EglContext& operator=(const EglContext&) = delete;
  ~EglContext() { Close(); }

  void Open()
  {
    setenv("EGL_PLATFORM", "surfaceless", 0);
    m_egl = dlopen("libEGL.so.1", RTLD_NOW | RTLD_GLOBAL);
    if (!m_egl)
      throw std::runtime_error("unable to load libEGL.so.1: " + DynamicLoaderError());
    m_gl = dlopen("libGL.so.1", RTLD_NOW | RTLD_GLOBAL);
    m_opengl = dlopen("libOpenGL.so.0", RTLD_NOW | RTLD_GLOBAL);
    LoadFunctions();

    auto platform_display = reinterpret_cast<GetPlatformDisplay>(m_get_proc("eglGetPlatformDisplay"));
    if (!platform_display)
      platform_display = reinterpret_cast<GetPlatformDisplay>(m_get_proc("eglGetPlatformDisplayEXT"));
    if (platform_display)
      m_display = platform_display(EGL_PLATFORM_SURFACELESS_MESA_VALUE, nullptr, nullptr);
    if (!m_display)
      m_display = m_get_display(nullptr);
    if (!m_display)
      throw std::runtime_error("EGL could not create a display");

    EGLint major = 0;
    EGLint minor = 0;
    if (m_initialize(m_display, &major, &minor) == EGL_FALSE_VALUE)
      throw std::runtime_error("EGL initialization failed");
    if (m_bind_api(EGL_OPENGL_API_VALUE) == EGL_FALSE_VALUE)
      throw std::runtime_error("EGL cannot bind the OpenGL API");

    const EGLint config_attributes[] = {
        EGL_SURFACE_TYPE_VALUE, EGL_PBUFFER_BIT_VALUE,
        EGL_RENDERABLE_TYPE_VALUE, EGL_OPENGL_BIT_VALUE,
        EGL_RED_SIZE_VALUE, 8, EGL_GREEN_SIZE_VALUE, 8, EGL_BLUE_SIZE_VALUE, 8,
        EGL_ALPHA_SIZE_VALUE, 8, EGL_NONE_VALUE};
    EGLint count = 0;
    if (m_choose_config(m_display, config_attributes, &m_config, 1, &count) == EGL_FALSE_VALUE || count != 1)
      throw std::runtime_error("EGL could not select an OpenGL pbuffer configuration");

    const EGLint surface_attributes[] = {
        EGL_PBUFFER_WIDTH_VALUE, 16, EGL_PBUFFER_HEIGHT_VALUE, 16, EGL_NONE_VALUE};
    m_surface = m_create_pbuffer_surface(m_display, m_config, surface_attributes);
    if (!m_surface)
      throw std::runtime_error("EGL could not create a pbuffer surface");
    const EGLint core_context_attributes[] = {
        EGL_CONTEXT_MAJOR_VERSION_KHR_VALUE, 3, EGL_CONTEXT_MINOR_VERSION_KHR_VALUE, 3,
        EGL_CONTEXT_OPENGL_PROFILE_MASK_KHR_VALUE, EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT_KHR_VALUE,
        EGL_NONE_VALUE};
    m_context = m_create_context(m_display, m_config, nullptr, core_context_attributes);
    if (!m_context)
      m_context = m_create_context(m_display, m_config, nullptr, nullptr);
    if (!m_context)
      throw std::runtime_error("EGL could not create an OpenGL context");
    if (m_make_current(m_display, m_surface, m_surface, m_context) == EGL_FALSE_VALUE)
      throw std::runtime_error("EGL could not make its OpenGL context current");
  }

  void Close()
  {
    if (m_display && m_make_current)
      m_make_current(m_display, nullptr, nullptr, nullptr);
    if (m_display && m_surface && m_destroy_surface)
      m_destroy_surface(m_display, m_surface);
    if (m_display && m_context && m_destroy_context)
      m_destroy_context(m_display, m_context);
    if (m_display && m_terminate)
      m_terminate(m_display);
    m_surface = nullptr;
    m_context = nullptr;
    m_display = nullptr;
    if (m_opengl)
      dlclose(m_opengl);
    if (m_gl)
      dlclose(m_gl);
    if (m_egl)
      dlclose(m_egl);
    m_opengl = nullptr;
    m_gl = nullptr;
    m_egl = nullptr;
  }

  void* GetProcAddress(const char* name) const
  {
    if (m_get_proc)
      if (void* proc = m_get_proc(name))
        return proc;
    if (m_opengl)
      if (void* proc = dlsym(m_opengl, name))
        return proc;
    if (m_gl)
      if (void* proc = dlsym(m_gl, name))
        return proc;
    return m_egl ? dlsym(m_egl, name) : nullptr;
  }

private:
  using GetDisplay = EGLDisplay (*)(void*);
  using GetPlatformDisplay = EGLDisplay (*)(EGLenum, void*, const EGLint*);
  using Initialize = EGLBoolean (*)(EGLDisplay, EGLint*, EGLint*);
  using BindApi = EGLBoolean (*)(EGLenum);
  using ChooseConfig = EGLBoolean (*)(EGLDisplay, const EGLint*, EGLConfig*, EGLint, EGLint*);
  using CreatePbufferSurface = EGLSurface (*)(EGLDisplay, EGLConfig, const EGLint*);
  using CreateContext = EGLContext (*)(EGLDisplay, EGLConfig, EGLContext, const EGLint*);
  using MakeCurrent = EGLBoolean (*)(EGLDisplay, EGLSurface, EGLSurface, EGLContext);
  using DestroySurface = EGLBoolean (*)(EGLDisplay, EGLSurface);
  using DestroyContext = EGLBoolean (*)(EGLDisplay, EGLContext);
  using Terminate = EGLBoolean (*)(EGLDisplay);
  using GetProcAddressFn = void* (*)(const char*);

  template <typename T>
  T Load(const char* name)
  {
    void* function = dlsym(m_egl, name);
    if (!function)
      throw std::runtime_error(std::string("EGL function unavailable: ") + name);
    return reinterpret_cast<T>(function);
  }

  void LoadFunctions()
  {
    m_get_display = Load<GetDisplay>("eglGetDisplay");
    m_initialize = Load<Initialize>("eglInitialize");
    m_bind_api = Load<BindApi>("eglBindAPI");
    m_choose_config = Load<ChooseConfig>("eglChooseConfig");
    m_create_pbuffer_surface = Load<CreatePbufferSurface>("eglCreatePbufferSurface");
    m_create_context = Load<CreateContext>("eglCreateContext");
    m_make_current = Load<MakeCurrent>("eglMakeCurrent");
    m_destroy_surface = Load<DestroySurface>("eglDestroySurface");
    m_destroy_context = Load<DestroyContext>("eglDestroyContext");
    m_terminate = Load<Terminate>("eglTerminate");
    m_get_proc = Load<GetProcAddressFn>("eglGetProcAddress");
  }

  void* m_egl = nullptr;
  void* m_gl = nullptr;
  void* m_opengl = nullptr;
  EGLDisplay m_display = nullptr;
  EGLConfig m_config = nullptr;
  EGLSurface m_surface = nullptr;
  EGLContext m_context = nullptr;
  GetDisplay m_get_display = nullptr;
  Initialize m_initialize = nullptr;
  BindApi m_bind_api = nullptr;
  ChooseConfig m_choose_config = nullptr;
  CreatePbufferSurface m_create_pbuffer_surface = nullptr;
  CreateContext m_create_context = nullptr;
  MakeCurrent m_make_current = nullptr;
  DestroySurface m_destroy_surface = nullptr;
  DestroyContext m_destroy_context = nullptr;
  Terminate m_terminate = nullptr;
  GetProcAddressFn m_get_proc = nullptr;
};

struct ControllerState {
  uint32_t buttons = 0;
  int16_t left_x = 0;
  int16_t left_y = 0;
  int16_t right_x = 0;
  int16_t right_y = 0;
  int16_t left_trigger = 0;
  int16_t right_trigger = 0;
};

struct MemoryMap {
  uint8_t* data = nullptr;
  uint64_t guest_start = 0;
  size_t size = 0;
  unsigned flags = 0;
};

struct CoreApi {
  void* library = nullptr;
  decltype(&retro_set_environment) set_environment = nullptr;
  decltype(&retro_set_video_refresh) set_video_refresh = nullptr;
  decltype(&retro_set_audio_sample) set_audio_sample = nullptr;
  decltype(&retro_set_audio_sample_batch) set_audio_sample_batch = nullptr;
  decltype(&retro_set_input_poll) set_input_poll = nullptr;
  decltype(&retro_set_input_state) set_input_state = nullptr;
  decltype(&retro_init) init = nullptr;
  decltype(&retro_deinit) deinit = nullptr;
  decltype(&retro_get_system_info) get_system_info = nullptr;
  decltype(&retro_load_game) load_game = nullptr;
  decltype(&retro_unload_game) unload_game = nullptr;
  decltype(&retro_set_controller_port_device) set_controller_port_device = nullptr;
  decltype(&retro_run) run = nullptr;
  decltype(&retro_serialize_size) serialize_size = nullptr;
  decltype(&retro_serialize) serialize = nullptr;
  decltype(&retro_unserialize) unserialize = nullptr;
  decltype(&retro_get_memory_data) get_memory_data = nullptr;
  decltype(&retro_get_memory_size) get_memory_size = nullptr;

  ~CoreApi() { Close(); }

  void Open(const std::string& path)
  {
    library = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
    if (!library)
      throw std::runtime_error("unable to load core " + path + ": " + DynamicLoaderError());
    set_environment = Require<decltype(set_environment)>("retro_set_environment");
    set_video_refresh = Require<decltype(set_video_refresh)>("retro_set_video_refresh");
    set_audio_sample = Require<decltype(set_audio_sample)>("retro_set_audio_sample");
    set_audio_sample_batch = Require<decltype(set_audio_sample_batch)>("retro_set_audio_sample_batch");
    set_input_poll = Require<decltype(set_input_poll)>("retro_set_input_poll");
    set_input_state = Require<decltype(set_input_state)>("retro_set_input_state");
    init = Require<decltype(init)>("retro_init");
    deinit = Require<decltype(deinit)>("retro_deinit");
    get_system_info = Require<decltype(get_system_info)>("retro_get_system_info");
    load_game = Require<decltype(load_game)>("retro_load_game");
    unload_game = Require<decltype(unload_game)>("retro_unload_game");
    set_controller_port_device = Require<decltype(set_controller_port_device)>("retro_set_controller_port_device");
    run = Require<decltype(run)>("retro_run");
    serialize_size = Require<decltype(serialize_size)>("retro_serialize_size");
    serialize = Require<decltype(serialize)>("retro_serialize");
    unserialize = Require<decltype(unserialize)>("retro_unserialize");
    get_memory_data = Require<decltype(get_memory_data)>("retro_get_memory_data");
    get_memory_size = Require<decltype(get_memory_size)>("retro_get_memory_size");
  }

  void Close()
  {
    if (library)
      dlclose(library);
    library = nullptr;
  }

private:
  template <typename T>
  T Require(const char* name)
  {
    void* function = dlsym(library, name);
    if (!function)
      throw std::runtime_error(std::string("core entry point unavailable: ") + name);
    return reinterpret_cast<T>(function);
  }
};

struct Options {
  std::string core_path;
  std::string rom_path;
  std::string system_dir;
  std::string save_dir;
};

class CoreSession;
CoreSession* g_session = nullptr;

class CoreSession {
public:
  explicit CoreSession(Options options) : m_options(std::move(options)) {}
  CoreSession(const CoreSession&) = delete;
  CoreSession& operator=(const CoreSession&) = delete;
  ~CoreSession() { Stop(); }

  void Start()
  {
    if (g_session)
      throw std::runtime_error("only one core session may exist in a runner process");
    std::error_code error;
    std::filesystem::create_directories(m_options.save_dir, error);
    if (error)
      throw std::runtime_error("cannot create runtime directory: " + error.message());
    m_egl.Open();
    m_core.Open(m_options.core_path);
    g_session = this;
    m_core.set_environment(Environment);
    m_core.set_video_refresh(VideoRefresh);
    m_core.set_audio_sample(AudioSample);
    m_core.set_audio_sample_batch(AudioSampleBatch);
    m_core.set_input_poll(InputPoll);
    m_core.set_input_state(InputState);
    m_core.init();
    retro_system_info info{};
    m_core.get_system_info(&info);
    m_library_name = info.library_name ? info.library_name : "unknown";
    m_library_version = info.library_version ? info.library_version : "unknown";
    retro_game_info game{};
    game.path = m_options.rom_path.c_str();
    if (!m_core.load_game(&game))
      throw std::runtime_error("retro_load_game rejected the ROM");
    m_game_loaded = true;
    for (unsigned port = 0; port < m_controllers.size(); ++port)
      m_core.set_controller_port_device(port, RETRO_DEVICE_JOYPAD);
    RunFrames(1);  // Publishes the MEM1 map.
    if (!m_memory.data)
    {
      m_memory.data = static_cast<uint8_t*>(m_core.get_memory_data(RETRO_MEMORY_SYSTEM_RAM));
      m_memory.size = m_core.get_memory_size(RETRO_MEMORY_SYSTEM_RAM);
      m_memory.guest_start = 0x80000000;
      m_memory.flags = RETRO_MEMDESC_BIGENDIAN | RETRO_MEMORY_SYSTEM_RAM;
    }
    if (!m_memory.data || !m_memory.size)
      throw std::runtime_error("the core did not expose GameCube system RAM after its first frame");
  }

  void Stop()
  {
    if (g_session != this)
      return;
    if (m_game_loaded)
    {
      m_core.unload_game();
      m_game_loaded = false;
    }
    m_core.deinit();
    if (m_hw.context_destroy)
      m_hw.context_destroy();
    g_session = nullptr;
  }

  void RunFrames(unsigned frames)
  {
    if (!frames)
      throw std::runtime_error("frame count must be positive");
    for (unsigned frame = 0; frame < frames; ++frame)
      m_core.run();
    m_frames += frames;
  }

  void SetControllers(const std::array<ControllerState, 4>& controllers)
  {
    std::lock_guard<std::mutex> guard(m_controller_mutex);
    m_controllers = controllers;
  }

  MemoryMap memory() const { return m_memory; }
  uint64_t frames() const { return m_frames; }
  uint64_t polls() const { return m_polls.load(); }
  uint64_t queries(unsigned port) const { return m_queries.at(port).load(); }
  uint64_t nonzero_queries(unsigned port) const { return m_nonzero_queries.at(port).load(); }
  const std::string& library_name() const { return m_library_name; }
  const std::string& library_version() const { return m_library_version; }

  bool SawGameId(std::string_view id) const
  {
    std::lock_guard<std::mutex> guard(m_log_mutex);
    return m_logs.find(id) != std::string::npos;
  }

  std::vector<uint8_t> Read(uint64_t guest_address, size_t length) const
  {
    const size_t offset = Offset(guest_address, length);
    return {m_memory.data + offset, m_memory.data + offset + length};
  }

  void Write(uint64_t guest_address, const std::vector<uint8_t>& bytes)
  {
    const size_t offset = Offset(guest_address, bytes.size());
    std::memcpy(m_memory.data + offset, bytes.data(), bytes.size());
  }

  std::vector<uint8_t> Snapshot()
  {
    const size_t size = m_core.serialize_size();
    if (!size)
      throw std::runtime_error("the core reported a zero savestate size");
    std::vector<uint8_t> snapshot(size);
    if (!m_core.serialize(snapshot.data(), snapshot.size()))
      throw std::runtime_error("retro_serialize failed");
    return snapshot;
  }

  void Restore(const std::vector<uint8_t>& snapshot)
  {
    if (snapshot.empty() || !m_core.unserialize(snapshot.data(), snapshot.size()))
      throw std::runtime_error("retro_unserialize failed");
    m_memory.data = static_cast<uint8_t*>(m_core.get_memory_data(RETRO_MEMORY_SYSTEM_RAM));
    m_memory.size = m_core.get_memory_size(RETRO_MEMORY_SYSTEM_RAM);
  }

  static bool Environment(unsigned command, void* data)
  {
    return g_session && g_session->HandleEnvironment(command, data);
  }
  static void VideoRefresh(const void*, unsigned, unsigned, size_t) {}
  static void AudioSample(int16_t, int16_t) {}
  static size_t AudioSampleBatch(const int16_t*, size_t frames) { return frames; }
  static void InputPoll()
  {
    if (g_session)
      g_session->m_polls.fetch_add(1);
  }
  static int16_t InputState(unsigned port, unsigned device, unsigned index, unsigned id)
  {
    return g_session ? g_session->ReadInput(port, device, index, id) : 0;
  }
  static void Log(retro_log_level, const char* format, ...)
  {
    if (!g_session)
      return;
    char message[2048];
    va_list args;
    va_start(args, format);
    std::vsnprintf(message, sizeof(message), format, args);
    va_end(args);
    {
      std::lock_guard<std::mutex> guard(g_session->m_log_mutex);
      if (g_session->m_logs.size() < 262144)
        g_session->m_logs.append(message);
    }
    std::fputs(message, stderr);
  }
  static retro_proc_address_t GLProcAddress(const char* name)
  {
    return reinterpret_cast<retro_proc_address_t>(
        g_session ? g_session->m_egl.GetProcAddress(name) : nullptr);
  }
  static uintptr_t CurrentFramebuffer() { return 0; }

private:
  size_t Offset(uint64_t guest_address, size_t length) const
  {
    if (guest_address < m_memory.guest_start || length > m_memory.size ||
        guest_address - m_memory.guest_start > m_memory.size - length)
      throw std::runtime_error("memory access is outside the MEM1 mapping");
    return static_cast<size_t>(guest_address - m_memory.guest_start);
  }

  bool HandleEnvironment(unsigned command, void* data)
  {
    switch (command)
    {
    case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
      *static_cast<const char**>(data) = m_options.system_dir.c_str();
      return true;
    case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
      *static_cast<const char**>(data) = m_options.save_dir.c_str();
      return true;
    case RETRO_ENVIRONMENT_GET_CORE_ASSETS_DIRECTORY:
      *static_cast<const char**>(data) = m_options.system_dir.c_str();
      return true;
    case RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
      static_cast<retro_log_callback*>(data)->log = Log;
      return true;
    case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
    case RETRO_ENVIRONMENT_SET_CONTROLLER_INFO:
    case RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:
    case RETRO_ENVIRONMENT_SET_VARIABLES:
    case RETRO_ENVIRONMENT_SET_CORE_OPTIONS:
    case RETRO_ENVIRONMENT_SET_CORE_OPTIONS_INTL:
    case RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2:
    case RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2_INTL:
    case RETRO_ENVIRONMENT_SET_GEOMETRY:
    case RETRO_ENVIRONMENT_SET_SYSTEM_AV_INFO:
    case RETRO_ENVIRONMENT_SET_MESSAGE:
      return true;
    case RETRO_ENVIRONMENT_GET_VARIABLE:
    {
      auto* variable = static_cast<retro_variable*>(data);
      const auto found = m_variables.find(variable->key ? variable->key : "");
      if (found == m_variables.end())
        return false;
      variable->value = found->second.c_str();
      return true;
    }
    case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
      *static_cast<bool*>(data) = false;
      return true;
    case RETRO_ENVIRONMENT_GET_CAN_DUPE:
      *static_cast<bool*>(data) = true;
      return true;
    case RETRO_ENVIRONMENT_GET_FASTFORWARDING:
      *static_cast<bool*>(data) = true;
      return true;
    case RETRO_ENVIRONMENT_GET_PREFERRED_HW_RENDER:
      *static_cast<retro_hw_context_type*>(data) = RETRO_HW_CONTEXT_OPENGL_CORE;
      return true;
    case RETRO_ENVIRONMENT_SET_HW_SHARED_CONTEXT:
      return true;
    case RETRO_ENVIRONMENT_SET_HW_RENDER:
    {
      // This is a bidirectional ABI struct. The core reads get_proc_address
      // from its original instance after the callback returns, so update that
      // instance before retaining our shutdown callback copy.
      auto* callback = static_cast<retro_hw_render_callback*>(data);
      callback->get_proc_address = GLProcAddress;
      callback->get_current_framebuffer = CurrentFramebuffer;
      m_hw = *callback;
      if (m_hw.context_reset)
        m_hw.context_reset();
      return true;
    }
    case RETRO_ENVIRONMENT_SET_MEMORY_MAPS:
    {
      const auto* map = static_cast<const retro_memory_map*>(data);
      for (unsigned i = 0; i < map->num_descriptors; ++i)
      {
        const auto& descriptor = map->descriptors[i];
        if ((descriptor.flags & RETRO_MEMORY_SYSTEM_RAM) && descriptor.start == 0x80000000)
        {
          m_memory = {static_cast<uint8_t*>(descriptor.ptr), descriptor.start, descriptor.len,
                      static_cast<unsigned>(descriptor.flags)};
          return true;
        }
      }
      return true;
    }
    // Do not register a frame-time callback. The runner has no wall-clock pacing path.
    case RETRO_ENVIRONMENT_GET_TARGET_REFRESH_RATE:
    case RETRO_ENVIRONMENT_SET_FRAME_TIME_CALLBACK:
      return false;
    default:
      return false;
    }
  }

  int16_t ReadInput(unsigned port, unsigned device, unsigned index, unsigned id)
  {
    if (port >= m_controllers.size())
      return 0;
    m_queries[port].fetch_add(1);
    ControllerState controller;
    {
      std::lock_guard<std::mutex> guard(m_controller_mutex);
      controller = m_controllers[port];
    }
    int16_t result = 0;
    if (device == RETRO_DEVICE_JOYPAD && id < 32)
      result = (controller.buttons & (uint32_t{1} << id)) ? 1 : 0;
    else if (device == RETRO_DEVICE_ANALOG)
    {
      if (index == RETRO_DEVICE_INDEX_ANALOG_LEFT)
        result = id == RETRO_DEVICE_ID_ANALOG_X ? controller.left_x : controller.left_y;
      else if (index == RETRO_DEVICE_INDEX_ANALOG_RIGHT)
        result = id == RETRO_DEVICE_ID_ANALOG_X ? controller.right_x : controller.right_y;
    }
    if (result)
      m_nonzero_queries[port].fetch_add(1);
    return result;
  }

  Options m_options;
  EglContext m_egl;
  CoreApi m_core;
  bool m_game_loaded = false;
  retro_hw_render_callback m_hw{};
  MemoryMap m_memory;
  std::array<ControllerState, 4> m_controllers{};
  mutable std::mutex m_controller_mutex;
  std::array<std::atomic<uint64_t>, 4> m_queries{};
  std::array<std::atomic<uint64_t>, 4> m_nonzero_queries{};
  std::atomic<uint64_t> m_polls{0};
  uint64_t m_frames = 0;
  std::unordered_map<std::string, std::string> m_variables{
      {"dolphin_renderer", "Hardware"},
      {"dolphin_emulation_speed", "0.0"},
      {"dolphin_main_cpu_thread", "disabled"},
      {"dolphin_fastmem", "disabled"},
      {"dolphin_fastmem_arena", "disabled"},
      {"dolphin_skip_gc_bios", "enabled"},
      {"dolphin_dsp_hle", "enabled"}};
  std::string m_library_name;
  std::string m_library_version;
  mutable std::mutex m_log_mutex;
  std::string m_logs;
};

uint64_t Fnv1a64(const std::vector<uint8_t>& bytes)
{
  uint64_t hash = 14695981039346656037ULL;
  for (uint8_t byte : bytes)
  {
    hash ^= byte;
    hash *= 1099511628211ULL;
  }
  return hash;
}

std::string Hex(const std::vector<uint8_t>& bytes)
{
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (uint8_t byte : bytes)
    out << std::setw(2) << static_cast<unsigned>(byte);
  return out.str();
}

std::vector<uint8_t> FromHex(const std::string& text)
{
  if (text.size() % 2)
    throw std::runtime_error("hex payload has an odd length");
  std::vector<uint8_t> bytes;
  for (size_t position = 0; position < text.size(); position += 2)
    bytes.push_back(static_cast<uint8_t>(std::stoul(text.substr(position, 2), nullptr, 16)));
  return bytes;
}

uint64_t ParseUnsigned(const std::string& text)
{
  size_t position = 0;
  const uint64_t value = std::stoull(text, &position, 0);
  if (position != text.size())
    throw std::runtime_error("invalid unsigned integer: " + text);
  return value;
}

Options ParseOptions(int argc, char** argv)
{
  Options options;
  for (int index = 1; index < argc; ++index)
  {
    const std::string argument = argv[index];
    if (argument == "--server")
      continue;
    if (index + 1 >= argc)
      throw std::runtime_error("missing value for " + argument);
    const std::string value = argv[++index];
    if (argument == "--core")
      options.core_path = value;
    else if (argument == "--rom")
      options.rom_path = value;
    else if (argument == "--system-dir")
      options.system_dir = value;
    else if (argument == "--save-dir")
      options.save_dir = value;
    else
      throw std::runtime_error("unknown argument: " + argument);
  }
  if (options.core_path.empty() || options.rom_path.empty() || options.system_dir.empty() ||
      options.save_dir.empty())
    throw std::runtime_error("usage: sonic-libretro-runner --server --core PATH --rom PATH "
                             "--system-dir PATH --save-dir PATH");
  return options;
}

void RunServer(CoreSession& session)
{
  const MemoryMap memory = session.memory();
  std::cout << "READY memory_size=" << memory.size << " map_base=0x" << std::hex << memory.guest_start
            << std::dec << " map_size=" << memory.size << " map_flags=0x" << std::hex << memory.flags
            << std::dec << " library=" << session.library_name() << " version=" << session.library_version()
            << "\n" << std::flush;
  std::map<uint64_t, std::vector<uint8_t>> snapshots;
  uint64_t next_snapshot_id = 1;
  std::string line;
  while (std::getline(std::cin, line))
  {
    try
    {
      std::istringstream input(line);
      std::string command;
      input >> command;
      if (command == "STEP")
      {
        std::string frames_text;
        input >> frames_text;
        const unsigned frames = static_cast<unsigned>(ParseUnsigned(frames_text));
        std::array<ControllerState, 4> controllers;
        for (auto& controller : controllers)
        {
          std::string buttons;
          int left_x = 0, left_y = 0, right_x = 0, right_y = 0, left_trigger = 0, right_trigger = 0;
          input >> buttons >> left_x >> left_y >> right_x >> right_y >> left_trigger >> right_trigger;
          if (!input)
            throw std::runtime_error("STEP requires four complete controller states");
          controller = {static_cast<uint32_t>(ParseUnsigned(buttons)), static_cast<int16_t>(left_x),
                        static_cast<int16_t>(left_y), static_cast<int16_t>(right_x),
                        static_cast<int16_t>(right_y), static_cast<int16_t>(left_trigger),
                        static_cast<int16_t>(right_trigger)};
        }
        const uint64_t polls_before = session.polls();
        const uint64_t queries_before = session.queries(0);
        const uint64_t active_before = session.nonzero_queries(0);
        session.SetControllers(controllers);
        session.RunFrames(frames);
        std::cout << "OK STEPPED frames=" << frames << " total_frames=" << session.frames()
                  << " polls=" << session.polls() - polls_before
                  << " p0_queries=" << session.queries(0) - queries_before
                  << " p0_nonzero=" << session.nonzero_queries(0) - active_before << "\n";
      }
      else if (command == "READ")
      {
        std::string address, length;
        input >> address >> length;
        std::cout << "DATA " << Hex(session.Read(ParseUnsigned(address), static_cast<size_t>(ParseUnsigned(length))))
                  << "\n";
      }
      else if (command == "WRITE")
      {
        std::string address, bytes;
        input >> address >> bytes;
        session.Write(ParseUnsigned(address), FromHex(bytes));
        std::cout << "OK WROTE bytes=" << bytes.size() / 2 << "\n";
      }
      else if (command == "SNAPSHOT")
      {
        auto snapshot = session.Snapshot();
        const uint64_t id = next_snapshot_id++;
        const uint64_t checksum = Fnv1a64(snapshot);
        const size_t size = snapshot.size();
        snapshots.emplace(id, std::move(snapshot));
        std::cout << "OK SNAPSHOT id=" << id << " size=" << size << " checksum=0x" << std::hex
                  << checksum << std::dec << "\n";
      }
      else if (command == "RESTORE")
      {
        std::string id_text;
        input >> id_text;
        const auto found = snapshots.find(ParseUnsigned(id_text));
        if (found == snapshots.end())
          throw std::runtime_error("unknown snapshot id");
        session.Restore(found->second);
        std::cout << "OK RESTORED\n";
      }
      else if (command == "HEALTH")
      {
        const MemoryMap current_memory = session.memory();
        std::cout << "OK HEALTH total_frames=" << session.frames() << " memory_size=" << current_memory.size
                  << " map_base=0x" << std::hex << current_memory.guest_start << std::dec
                  << " map_size=" << current_memory.size << " map_flags=0x" << std::hex
                  << current_memory.flags << std::dec << " game_id_GXEE8P="
                  << (session.SawGameId("GXEE8P") ? 1 : 0) << "\n";
      }
      else if (command == "QUIT")
      {
        std::cout << "OK BYE\n" << std::flush;
        return;
      }
      else
      {
        throw std::runtime_error("unknown command");
      }
    }
    catch (const std::exception& error)
    {
      std::cout << "ERROR " << error.what() << "\n";
    }
    std::cout << std::flush;
  }
}

}  // namespace

int main(int argc, char** argv)
{
  try
  {
    CoreSession session(ParseOptions(argc, argv));
    session.Start();
    RunServer(session);
    return 0;
  }
  catch (const std::exception& error)
  {
    std::cerr << "sonic-libretro-runner: " << error.what() << "\n";
    return 1;
  }
}
