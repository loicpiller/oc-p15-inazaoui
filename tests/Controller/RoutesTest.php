<?php

namespace App\Tests\Controller;

use App\Kernel;
use PHPUnit\Framework\TestCase;
use Symfony\Component\Filesystem\Filesystem;
use Symfony\Component\Routing\Generator\UrlGeneratorInterface;
use Symfony\Component\Routing\RouterInterface;

class RoutesTest extends TestCase
{
    public function testControllerRoutesKeepTheirDefinitions(): void
    {
        // Keep this route cache isolated so the assertions exercise a fresh kernel.
        $cacheDir = sys_get_temp_dir().'/routes-test-'.bin2hex(random_bytes(8));
        $kernel = new RoutesTestKernel('test', true, $cacheDir);

        try {
            $kernel->boot();
            /** @var RouterInterface $router */
            $router = $kernel->getContainer()->get('router');
            $routes = $router->getRouteCollection();
            // Preserve the established route names, paths and controller targets after the attribute migration.
            $expected = [
                'home' => ['/', 'App\\Controller\\HomeController::home'],
                'guests' => ['/guests', 'App\\Controller\\HomeController::guests'],
                'guest' => ['/guest/{id}', 'App\\Controller\\HomeController::guest'],
                'portfolio' => ['/portfolio/{id}', 'App\\Controller\\HomeController::portfolio'],
                'about' => ['/about', 'App\\Controller\\HomeController::about'],
                'admin_login' => ['/login', 'App\\Controller\\Admin\\SecurityController::login'],
                'admin_album_index' => ['/admin/album', 'App\\Controller\\Admin\\AlbumController::index'],
                'admin_album_add' => ['/admin/album/add', 'App\\Controller\\Admin\\AlbumController::add'],
                'admin_album_update' => ['/admin/album/update/{id}', 'App\\Controller\\Admin\\AlbumController::update'],
                'admin_album_delete' => ['/admin/album/delete/{id}', 'App\\Controller\\Admin\\AlbumController::delete'],
                'admin_media_index' => ['/admin/media', 'App\\Controller\\Admin\\MediaController::index'],
                'admin_media_add' => ['/admin/media/add', 'App\\Controller\\Admin\\MediaController::add'],
                'admin_media_delete' => ['/admin/media/delete/{id}', 'App\\Controller\\Admin\\MediaController::delete'],
            ];

            foreach ($expected as $name => [$path, $controller]) {
                $route = $routes->get($name);
                self::assertNotNull($route, $name);
                self::assertSame($path, $route->getPath(), $name);
                self::assertSame(['_controller' => $controller] + ('portfolio' === $name ? ['id' => null] : []), $route->getDefaults(), $name);
                self::assertSame([], $route->getRequirements(), $name);
                self::assertSame([], $route->getMethods(), $name);
                self::assertSame([], $route->getSchemes(), $name);
            }

            // The portfolio id stays optional for both URL generation and route matching.
            self::assertSame('/portfolio', $router->generate('portfolio', [], UrlGeneratorInterface::ABSOLUTE_PATH));
            self::assertSame('/portfolio/42', $router->generate('portfolio', ['id' => 42]));
            self::assertSame('portfolio', $router->match('/portfolio')['_route']);
            self::assertSame('42', $router->match('/portfolio/42')['id']);
        } finally {
            $kernel->shutdown();
            // Remove the isolated cache even when an assertion fails.
            (new Filesystem())->remove($cacheDir);
        }
    }
}

class RoutesTestKernel extends Kernel
{
    private $testCacheDir;

    public function __construct(string $environment, bool $debug, string $testCacheDir)
    {
        $this->testCacheDir = $testCacheDir;
        parent::__construct($environment, $debug);
    }

    public function getProjectDir(): string
    {
        return dirname(__DIR__, 2);
    }

    public function getCacheDir(): string
    {
        return $this->testCacheDir;
    }
}
