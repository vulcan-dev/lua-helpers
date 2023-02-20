from argparse import ArgumentParser
import os
import sys
from requests import get
from tqdm import tqdm
import tarfile
import shutil
from distutils import ccompiler

force = False

def download_lua(version, arch):
    filename = f'lua-{version}.tar.gz'

    if os.path.exists(f'downloads/{filename}'):
        if not force:
            print(f'{filename} already exists, skipping...')
            return
        else:
            os.remove(f'downloads/{filename}')
            
    try:
        download_file(f'https://www.lua.org/ftp/{filename}', 'downloads')
    except Exception as e:
        print(f'Failed to download Lua {version}: {e}')

    while os.path.exists(f'downloads/{filename}.part'):
        pass

    if os.path.exists(f'downloads/lua-{version}'):
        try:
            shutil.rmtree(f'downloads/lua-{version}')
        except Exception as e:
            print(f'Failed to remove lua-{version}: {e}')
            return False

    extract_file(f'downloads/{filename}')
    if os.path.exists(f'downloads/lua'): # Older versions of Lua don't have the version number in the folder name
        try:
            os.rename(f'downloads/lua', f'downloads/lua-{version}')
        except Exception as e:
            print(f'Failed to rename lua to lua-{version}: {e}')
            return False

    if os.path.exists(f'downloads/{filename}'):
        try:
            os.remove(f'downloads/{filename}')
        except Exception as e:
            print(f'Failed to remove {filename}: {e}')

    compile_lua(version, arch)

def download_file(url, path, force=True, progress=True):
    filename = url.split('/')[-1]

    if os.path.exists(f'{path}/{filename}'):
        if not force:
            print(f'{filename} already exists, skipping...')
            return
        else:
            os.remove(f'{path}/{filename}')

    print(f'Downloading {filename}...')

    try:
        response = get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        progress = tqdm(total=total_size, unit='iB', unit_scale=True)
        with open(f'{path}/{filename}', 'wb') as file:
            for data in response.iter_content(block_size):
                progress.update(len(data))
                file.write(data)
        progress.close()
        if total_size != 0 and progress.n != total_size:
            print('ERROR, something went wrong')
    except Exception as e:
        print(f'Failed to download {filename}: {e}')

    while os.path.exists(f'{path}/{filename}.part'):
        pass

def extract_file(file, path='downloads'):
    try:
        tar = tarfile.open(file)
        tar.extractall(path)
        tar.close()
    except Exception as e:
        print(f'Failed to extract {file}: {e}')
        return False

    print(f'Extracted {file} to {path}')

    return True

def compile_lua(version, arch):
    number_version = version.split('.')
    number_version = [int(n) for n in number_version]
    if number_version[0] == 5 and number_version[1] <= 1:
        print('Lua versions below 5.2 are not supported (yet)')
        return

    stripped_version = version.replace('.', '')[:2]

    # Get compiler
    compiler = ccompiler.new_compiler()
    os.chdir(f'downloads/lua-{version}/')

    include_dir = os.path.join(os.getcwd(), 'include')
    print(f'include_dir: {include_dir}')

    if os.path.exists('include'):
        compiler.add_include_dir(include_dir)

    os.chdir('src')
    files = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.c')]

    for file in os.listdir('.'):
        if file.endswith('.obj') or file.endswith('.o') or file.endswith('.exe') or file.endswith('.lib') or file.endswith('.dll'):
            os.remove(file)

    # Compile all .c files into .obj
    for file in files:
        compiler.compile([file], output_dir='.', extra_postargs=['/MD', '/O2', '/c', f'/DLUA_BUILD_AS_DLL'])

    # Rename two special files
    os.rename('lua.obj', f'lua{stripped_version}.o')
    os.rename('luac.obj', f'luac{stripped_version}.o')

    # Link up all the other .objs into a .lib and .dll file
    print('Linking up all the other .objs into a .lib and .dll file')
    objects = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.obj')]
    compiler.link_shared_lib(objects, f'lua{stripped_version}', '.', extra_postargs=['/DLL', f'/IMPLIB:lua{stripped_version}.lib', f'/OUT:lua{stripped_version}.dll'])

    # Link lua into an .exe
    print('Linking lua into an .exe')
    compiler.link_executable([f'lua{stripped_version}.o'], f'lua{stripped_version}', '.', libraries=[f'lua{stripped_version}'], extra_postargs=[f'/OUT:lua{stripped_version}.exe'])

    # Create static library
    print('Creating static library')
    compiler.create_static_lib(objects, f'lua{stripped_version}-static', '.')

    # Create luac
    print('Creating luac')
    compiler.link_executable([f'luac{stripped_version}.o'], f'luac{stripped_version}', '.', libraries=[f'lua{stripped_version}-static'], extra_postargs=[f'/OUT:luac{stripped_version}.exe'])
    
    # Copy files to the correct location
    print('Copying files to the correct location')
    os.chdir('../..')
    if not os.path.exists(f'lua-{version}/bin'):
        os.mkdir(f'lua-{version}/bin')

    shutil.copy(f'lua-{version}/src/lua{stripped_version}.exe', f'lua-{version}/bin/lua{stripped_version}.exe')
    shutil.copy(f'lua-{version}/src/luac{stripped_version}.exe', f'lua-{version}/bin/luac{stripped_version}.exe')
    shutil.copy(f'lua-{version}/src/lua{stripped_version}.dll', f'lua-{version}/bin/lua{stripped_version}.dll')

    # Copy headers
    print('Copying headers')
    if not os.path.exists(f'lua-{version}/include'):
        os.mkdir(f'lua-{version}/include')

    shutil.copy(f'lua-{version}/src/lua.h', f'lua-{version}/include/lua.h')
    shutil.copy(f'lua-{version}/src/luaconf.h', f'lua-{version}/include/luaconf.h')
    shutil.copy(f'lua-{version}/src/lualib.h', f'lua-{version}/include/lualib.h')
    shutil.copy(f'lua-{version}/src/lauxlib.h', f'lua-{version}/include/lauxlib.h')
    shutil.copy(f'lua-{version}/src/lua.hpp', f'lua-{version}/include/lua.hpp')

    # Make lib folder
    print('Making lib folder')
    if not os.path.exists(f'lua-{version}/lib'):
        os.mkdir(f'lua-{version}/lib')

    shutil.copy(f'lua-{version}/src/lua{stripped_version}.lib', f'lua-{version}/lib/lua{stripped_version}.lib')
    shutil.copy(f'lua-{version}/src/lua{stripped_version}-static.lib', f'lua-{version}/lib/lua-static{stripped_version}.lib')

def main():
    # if not ctypes.windll.shell32.IsUserAnAdmin():
    #     ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    #     return

    parser = ArgumentParser()
    parser.add_argument('--download', '-d', help='Set to download mode', default=False, action='store_true')
    parser.add_argument('--lua', '-l', help='Lua version to download, check https://www.lua.org/ftp/ for available versions')
    # parser.add_argument('--luasocket', '-s', help='Downloads LuaSocket for the given Lua version')
    # parser.add_argument('--arch', '-a', help='Architecture to download Lua for', default='x64')
    parser.add_argument('--force', '-f', help='Force download even if file already exists', default=False, action='store_true')
    args = parser.parse_args()

    global force
    force = args.force

    if (not args.download) and args.lua or args.luasocket:
        print('You can only download Lua or LuaSocket in download mode')
        return

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    if args.download:
        if args.lua:
            download_lua(args.lua, args.arch)

if __name__ == '__main__':
    main()