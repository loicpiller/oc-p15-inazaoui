<?php

namespace App\Tests\Controller;

use Symfony\Bundle\FrameworkBundle\Test\WebTestCase;

class FunctionalTest extends WebTestCase
{
    public function testPublicPagesAndAccessControl(): void
    {
        $client = static::createClient();
        // Public pages, including login, remain available without authentication.
        foreach (['/', '/about', '/guests', '/portfolio', '/login'] as $path) {
            $client->request('GET', $path);
            self::assertResponseIsSuccessful($path);
        }
        $client->request('GET', '/admin/album');
        self::assertResponseRedirects('http://localhost/login');
        // An invalid login is rejected with an error before valid credentials grant access.
        $client->request('POST', '/login', ['_username' => 'ina', '_password' => 'invalid-test-password']);
        self::assertResponseRedirects('http://localhost/login');
        $client->followRedirect();
        self::assertResponseIsSuccessful();
        self::assertSelectorExists('.alert-danger');
        $client->request('POST', '/login', ['_username' => 'ina', '_password' => 'password']);
        self::assertResponseRedirects();
        $client->request('GET', '/admin/album/add');
        self::assertResponseIsSuccessful();
    }
}
